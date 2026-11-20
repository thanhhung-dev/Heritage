"""Durable PostgreSQL classification consumer; run separately from page requests."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
import sys
from uuid import uuid4

from dotenv import load_dotenv
from sqlalchemy import and_, or_, select, update

from apps.backend.db.base import AsyncSessionLocal, configure_database, dispose_database
from apps.backend.models.heritage_classification import ClassificationJob, CulturalContent
from apps.backend.services.classification_semantic import configured_semantic
from apps.backend.services.classification_input import classification_input
from apps.backend.services.classification_store import apply_prediction
from apps.backend.services.heritage_classifier import ContentInput, classify

log = logging.getLogger(__name__)


async def run_next(factory=AsyncSessionLocal, *, classifier=classify, run_id=None,
                   high=0.9, medium=0.55, lease_seconds=120, max_attempts=5):
    now = datetime.now(timezone.utc)
    async with factory() as db:
        await db.execute(update(ClassificationJob).where(ClassificationJob.status == "RUNNING",
            ClassificationJob.leased_until < now, ClassificationJob.attempts >= max_attempts).values(
                status="FAILED", lease_token=None, leased_until=None, last_error="Worker lease exhausted; review and requeue."))
        job = (await db.scalars(select(ClassificationJob).where(
            or_(ClassificationJob.status.in_(["PENDING", "RETRY"]),
                and_(ClassificationJob.status == "RUNNING", ClassificationJob.leased_until < now)),
            ClassificationJob.available_at <= now, ClassificationJob.attempts < max_attempts,
        ).order_by(ClassificationJob.available_at, ClassificationJob.content_id)
          .with_for_update(skip_locked=True).limit(1))).one_or_none()
        if job is None:
            await db.commit()
            return False
        job.status, job.lease_token = "RUNNING", str(uuid4())
        job.leased_until, job.attempts = now + timedelta(seconds=lease_seconds), job.attempts + 1
        content = await db.get(CulturalContent, job.content_id)
        content_id, generation, lease, attempts = job.content_id, job.generation, job.lease_token, job.attempts
        source = await classification_input(db, content)
        await db.commit()
    try:
        prediction = await asyncio.to_thread(classifier, source, semantic=configured_semantic())
        async with factory() as db:
            # Always lock content before job, matching the source-trigger order.
            content = (await db.scalars(select(CulturalContent).where(
                CulturalContent.id == content_id).with_for_update())).one_or_none()
            job = (await db.scalars(select(ClassificationJob).where(
                ClassificationJob.content_id == content_id).with_for_update())).one_or_none()
            if (content is None or job is None or content.input_revision != generation
                    or job.generation != generation or job.lease_token != lease or job.status != "RUNNING"):
                return True  # Newer source generation/claim owns the work.
            await apply_prediction(db, content, prediction, run_id=run_id or str(uuid4()), high=high, medium=medium)
            job.status, job.lease_token, job.leased_until, job.last_error = "DONE", None, None, None
            job.updated_at = datetime.now(timezone.utc)
            await db.commit()
            log.info("Classification applied content=%s generation=%s status=%s", content_id, generation,
                     content.classification_status)
    except Exception as error:
        async with factory() as db:
            await db.execute(update(ClassificationJob).where(
                ClassificationJob.content_id == content_id, ClassificationJob.generation == generation,
                ClassificationJob.lease_token == lease, ClassificationJob.status == "RUNNING",
            ).values(status="RETRY" if attempts < max_attempts else "FAILED", lease_token=None,
                leased_until=None, available_at=datetime.now(timezone.utc) + timedelta(seconds=min(300, 2**attempts)),
                last_error=f"Classification failed ({type(error).__name__}); inspect worker dependencies.",
                updated_at=datetime.now(timezone.utc)))
            await db.commit()
        log.warning("Classification retry content=%s generation=%s failure=%s", content_id, generation, type(error).__name__)
    return True


async def serve(args):
    configure_database(os.environ["DATABASE_URL"])
    try:
        count = 0
        while True:
            found = await run_next(high=args.high, medium=args.medium)
            if found:
                count += 1
            if args.once or (args.drain and not found):
                return
            if not found:
                await asyncio.sleep(args.poll_seconds)
    finally:
        await dispose_database()


def main():
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--drain", action="store_true", help="Process currently ready work and exit")
    parser.add_argument("--poll-seconds", type=float, default=2)
    parser.add_argument("--high", type=float, default=float(os.getenv("HERITAGE_CLASSIFICATION_HIGH", "0.9")))
    parser.add_argument("--medium", type=float, default=float(os.getenv("HERITAGE_CLASSIFICATION_MEDIUM", "0.55")))
    args = parser.parse_args()
    if not 0 <= args.medium < args.high <= 1 or not 0.1 <= args.poll_seconds <= 60:
        parser.error("Require 0 <= medium < high <= 1 and poll seconds in [0.1,60]")
    if not os.environ.get("DATABASE_URL", "").startswith("postgresql+psycopg://"):
        parser.error("DATABASE_URL must use postgresql+psycopg")
    logging.basicConfig(level=logging.INFO)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(serve(args))


if __name__ == "__main__":
    main()
