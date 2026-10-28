import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

from apps.backend.db.base import configure_database, dispose_database


async def main(database_url: str):
    engine = configure_database(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            print("Database connected:", result.scalar())
    finally:
        await dispose_database()


if __name__ == "__main__":
    from dotenv import load_dotenv
    from apps.backend.core.config import validate_startup_config

    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    settings = validate_startup_config()
    if not settings.database_url:
        raise SystemExit("DATABASE_URL is required for the manual database smoke check")
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    with asyncio.Runner(loop_factory=loop_factory) as runner:
        runner.run(main(settings.database_url))
