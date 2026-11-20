"""Build the next turn's bounded history after a chat turn is committed.

The worker does not call the LLM. A summary generated on the single llama.cpp
slot would stall chat and could be mistaken for evidence. PostgreSQL remains
authoritative; this process only copies the same bound `bounded_history` already
applies on a cache miss.
"""
from __future__ import annotations

import asyncio
import logging
import signal
from uuid import UUID

from sqlalchemy import select

from apps.backend.core.config import validate_startup_config
from apps.backend.core.observability import configure_logging
from apps.backend.db.base import AsyncSessionLocal, configure_database, dispose_database
from apps.backend.models.chat import ChatMessage, Conversation
from apps.backend.schemas.chat import MAX_CONTEXT_MESSAGES
from apps.backend.services.chat_context import bounded_history
from apps.backend.services.context_store import RedisContextStore, redis_settings

log = logging.getLogger(__name__)


async def refresh(session, store: RedisContextStore, conversation_id: UUID) -> None:
    exists = (await session.execute(
        select(Conversation.id).where(Conversation.id == conversation_id)
    )).scalar_one_or_none()
    if exists is None:
        await store.delete(conversation_id)
        return
    rows = (await session.execute(
        select(ChatMessage.id, ChatMessage.role, ChatMessage.content)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(MAX_CONTEXT_MESSAGES)
    )).all()
    if not rows:
        await store.delete(conversation_id)
        return
    await store.save(conversation_id, rows[0].id, bounded_history(rows))


async def serve() -> None:
    settings = validate_startup_config()
    configure_logging(settings.otel_service_name, settings.app_environment)
    if not settings.database_url:
        raise SystemExit("context worker requires DATABASE_URL")
    redis = redis_settings()
    if redis is None:
        raise SystemExit("context worker requires REDIS_HOST")
    configure_database(settings.database_url)
    import redis.asyncio as aioredis

    host, port, password = redis
    client = aioredis.Redis(
        host=host,
        port=port,
        password=password or None,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=None,
    )
    store = RedisContextStore(client)
    stop = asyncio.Event()
    try:
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, stop.set)
    except NotImplementedError:
        pass
    log.info("context worker ready")
    try:
        while not stop.is_set():
            await store.heartbeat()
            try:
                conversation_id = await store.pop()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.warning("context_job_pop_failed")
                await asyncio.sleep(1)
                continue
            if conversation_id is None:
                continue
            try:
                async with AsyncSessionLocal() as session:
                    await refresh(session, store, conversation_id)
            except Exception:
                log.warning("context_job_failed")
    finally:
        await client.aclose()
        await dispose_database()


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()
