"""Alembic env.py — async PostgreSQL with SQLAlchemy 2.0.

Migration guide §3.4: env.py đọc DATABASE_URL từ environment, import models
và gán target_metadata = Base.metadata. Không hardcode password vào alembic.ini.

Async note: Alembic v1.19+ hỗ trợ async engine. Online mode dùng async_engine;
offline mode render SQL string (không kết nối, chỉ cần URL để format).
"""
import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# Model metadata — nguồn đúng cho autogenerate
# ---------------------------------------------------------------------------
from backend.db.base import Base  # noqa: E402
from backend.models import *  # noqa: E402,F401

target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    """The ORM maps v_tour_stop for reads; Alembic manages it as a SQL view."""
    return not (type_ == "table" and name == "v_tour_stop")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

DATABASE_URL = os.getenv("DATABASE_URL", "")


def run_migrations_offline() -> None:
    """Render SQL string — không cần DBAPI connection."""
    url = DATABASE_URL or config.get_main_option("sqlalchemy.url")
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
    """Async engine — dùng DATABASE_URL trực tiếp (postgresql+psycopg://)."""
    connectable = async_engine_from_config(
        {"sqlalchemy.url": DATABASE_URL},
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
