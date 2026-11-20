"""Dry-run by default. --apply classifies; --rollback RUN_ID restores unchanged audited classifications."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def run(args):
    from apps.backend.db.base import AsyncSessionLocal, configure_database, dispose_database
    from apps.backend.services.classification_backfill import backfill, rollback
    configure_database(os.environ["DATABASE_URL"])
    try:
        result = (await rollback(AsyncSessionLocal, args.rollback) if args.rollback else
                  await backfill(AsyncSessionLocal, apply=args.apply, limit=args.limit, after_id=args.after_id))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        await dispose_database()


def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--rollback")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--after-id", type=int, default=0)
    args = parser.parse_args()
    if not 1 <= args.limit <= 10000 or args.after_id < 0:
        parser.error("limit must be 1..10000 and after-id nonnegative")
    if not os.environ.get("DATABASE_URL", "").startswith("postgresql+psycopg://"):
        parser.error("DATABASE_URL must use postgresql+psycopg")
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
