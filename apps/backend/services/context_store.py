"""Prepare bounded chat history in Redis. PostgreSQL stays the source of truth."""
from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Mapping
from uuid import UUID

from pydantic import ValidationError

from apps.backend.schemas.chat import (
    MAX_CONTEXT_CHARS,
    MAX_CONTEXT_MESSAGES,
    ChatContextMessage,
)

log = logging.getLogger(__name__)

JOBS_KEY = "heritage:ai:context:jobs"
SNAPSHOT_PREFIX = "heritage:ai:context:"
HEARTBEAT_KEY = "heritage:ai:context:worker"
SNAPSHOT_TTL_SECONDS = 24 * 60 * 60
HEARTBEAT_TTL_SECONDS = 30
CONNECT_TIMEOUT_SECONDS = 0.2
DOWN_SECONDS = 5.0

_client = None
_down_until = 0.0


def reset_client() -> None:
    """Drop the process-local client. Tests use this; request code uses mark_down."""
    global _client, _down_until
    _client = None
    _down_until = 0.0


def mark_down() -> None:
    global _client, _down_until
    _down_until = time.monotonic() + DOWN_SECONDS
    client = _client
    _client = None
    if client is None:
        return
    try:
        client.connection_pool.disconnect()
    except Exception:
        log.warning("context_redis_disconnect_failed")


def redis_settings(environ: Mapping[str, str] | None = None) -> tuple[str, int, str] | None:
    """Host is optional so chat keeps working when Redis is not configured."""
    env = os.environ if environ is None else environ
    host = env.get("REDIS_HOST", "").strip()
    if not host:
        return None
    raw_port = env.get("REDIS_PORT", "6379").strip() or "6379"
    try:
        port = int(raw_port)
    except ValueError:
        raise ValueError("REDIS_PORT must be 1-65535.") from None
    if port < 1 or port > 65535:
        raise ValueError("REDIS_PORT must be 1-65535.")
    return host, port, env.get("REDIS_PASSWORD", "").strip()


def history_if_fresh(payload: dict | None, latest_message_id) -> list[ChatContextMessage] | None:
    """Accept a snapshot only when it still ends at the latest saved message."""
    if not isinstance(payload, dict) or latest_message_id is None:
        return None
    if str(payload.get("through_message_id") or "") != str(latest_message_id):
        return None
    raw_history = payload.get("history")
    if not isinstance(raw_history, list) or len(raw_history) > MAX_CONTEXT_MESSAGES:
        return None
    try:
        history = [ChatContextMessage.model_validate(item) for item in raw_history]
    except ValidationError:
        return None
    if sum(len(message.content) for message in history) > MAX_CONTEXT_CHARS:
        return None
    return history


def snapshot_document(conversation_id: UUID, newest_message_id, history: list[ChatContextMessage]) -> str:
    return json.dumps({
        "conversation_id": str(conversation_id),
        "through_message_id": str(newest_message_id),
        "history": [message.model_dump() for message in history],
    }, ensure_ascii=False)


class RedisContextStore:
    def __init__(self, client):
        self.client = client

    async def load(self, conversation_id: UUID) -> dict | None:
        raw = await self.client.get(f"{SNAPSHOT_PREFIX}{conversation_id}")
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    async def save(self, conversation_id: UUID, newest_message_id, history: list[ChatContextMessage]) -> None:
        await self.client.set(
            f"{SNAPSHOT_PREFIX}{conversation_id}",
            snapshot_document(conversation_id, newest_message_id, history),
            ex=SNAPSHOT_TTL_SECONDS,
        )

    async def enqueue(self, conversation_id: UUID) -> None:
        await self.client.lpush(JOBS_KEY, str(conversation_id))

    async def delete(self, conversation_id: UUID) -> None:
        await self.client.delete(f"{SNAPSHOT_PREFIX}{conversation_id}")

    async def pop(self, timeout: int = 5) -> UUID | None:
        item = await self.client.brpop(JOBS_KEY, timeout=timeout)
        if not item:
            return None
        raw = item[1]
        return UUID(str(raw))

    async def heartbeat(self) -> None:
        await self.client.set(HEARTBEAT_KEY, "1", ex=HEARTBEAT_TTL_SECONDS)


def configured_store() -> RedisContextStore | None:
    global _client
    if time.monotonic() < _down_until:
        return None
    try:
        settings = redis_settings()
    except ValueError:
        log.warning("context_redis_config_invalid")
        return None
    if settings is None:
        return None
    if _client is None:
        import redis.asyncio as aioredis

        host, port, password = settings
        _client = aioredis.Redis(
            host=host,
            port=port,
            password=password or None,
            decode_responses=True,
            socket_connect_timeout=CONNECT_TIMEOUT_SECONDS,
            socket_timeout=CONNECT_TIMEOUT_SECONDS,
        )
    return RedisContextStore(_client)


async def enqueue_quietly(store: RedisContextStore | None, conversation_id: UUID) -> None:
    if store is None:
        return
    try:
        await store.enqueue(conversation_id)
    except Exception:
        mark_down()
        log.warning("context_enqueue_failed")


async def forget_quietly(store: RedisContextStore | None, conversation_id: UUID) -> None:
    if store is None:
        return
    try:
        await store.delete(conversation_id)
    except Exception:
        mark_down()
        log.warning("context_delete_failed")
