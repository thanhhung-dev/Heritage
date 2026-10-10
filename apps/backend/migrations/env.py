"""Alembic env.py — async PostgreSQL with SQLAlchemy 2.0.

Migration guide §3.4: env.py đọc DATABASE_URL từ environment, import models
và gán target_metadata = Base.metadata. Không hardcode password vào alembic.ini.

Async note: Alembic v1.19+ hỗ trợ async engine. Online mode dùng async_engine;
offline mode render SQL string (không kết nối, chỉ cần URL để format).
"""
import asyncio
import logging
import os
import sys
from logging.config import fileConfig
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.exc import ArgumentError
from sqlalchemy.engine import Connection
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_engine_from_config

from apps.backend.db.base import Base
from apps.backend.models import *

target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    """The ORM maps v_tour_stop for reads; Alembic manages it as a SQL view."""
    return not (type_ == "table" and name == "v_tour_stop")
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    logger.error(
        "DATABASE_URL is not set. Create a .env file from .env.example, "
        "set DATABASE_URL to a PostgreSQL URL using postgresql+psycopg:// "
        "or postgresql+asyncpg://, or export DATABASE_URL before running Alembic."
    )
    raise RuntimeError("DATABASE_URL is required to run Alembic migrations.")

try:
    database_url = make_url(DATABASE_URL)
except (ArgumentError, TypeError, ValueError) as exc:
    logger.error(
        "DATABASE_URL is invalid. Set it to a valid PostgreSQL URL using "
        "postgresql+psycopg:// or postgresql+asyncpg://."
    )
    raise RuntimeError("DATABASE_URL is not a valid SQLAlchemy URL.") from exc

if database_url.drivername not in {
    "postgresql+psycopg",
    "postgresql+asyncpg",
}:
    logger.error(
        "DATABASE_URL must use postgresql+psycopg:// or postgresql+asyncpg:// "
        "for async Alembic migrations."
    )
    raise RuntimeError("DATABASE_URL uses an unsupported PostgreSQL driver.")

# Escape interpolation markers for ConfigParser, which Alembic uses internally.
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))


def run_migrations_offline() -> None:
    """Render SQL string — không cần DBAPI connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Create the async engine using the validated DATABASE_URL."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
