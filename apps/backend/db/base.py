from __future__ import annotations

from datetime import datetime
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func

from apps.backend.core.config import DatabaseSettings

DATABASE_URL: str | None = None
DATABASE_SETTINGS: DatabaseSettings | None = None
engine: AsyncEngine | None = None
AsyncSessionLocal = async_sessionmaker(
    class_=AsyncSession,
    expire_on_commit=False,
)


def database_engine_options(settings: DatabaseSettings) -> dict[str, object]:
    """Build SQLAlchemy options without exposing the connection URL."""

    return {
        "echo": settings.echo,
        "hide_parameters": True,
        "pool_pre_ping": True,
        "pool_size": settings.pool_size,
        "max_overflow": settings.max_overflow,
        "pool_timeout": settings.pool_timeout,
        "pool_recycle": settings.pool_recycle,
        "connect_args": settings.connect_args,
    }


def configure_database(settings: DatabaseSettings) -> AsyncEngine:
    """Create and bind the database engine after startup validation succeeds."""

    global DATABASE_URL, DATABASE_SETTINGS, engine

    if engine is not None and DATABASE_SETTINGS == settings:
        return engine
    if engine is not None:
        raise RuntimeError(
            "Database engine is already configured; dispose it before reconfiguring."
        )

    DATABASE_URL = settings.url
    DATABASE_SETTINGS = settings
    engine = create_async_engine(
        settings.url,
        **database_engine_options(settings),
    )
    AsyncSessionLocal.configure(bind=engine)
    return engine


async def dispose_database() -> None:
    """Dispose the configured engine during application shutdown."""

    global DATABASE_URL, DATABASE_SETTINGS, engine

    if engine is not None:
        await engine.dispose()
    AsyncSessionLocal.configure(bind=None)
    DATABASE_URL = None
    DATABASE_SETTINGS = None
    engine = None


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Tables with created_at / updated_at managed by DB triggers (see schema.sql touch_updated_at)."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
