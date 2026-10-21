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

DATABASE_URL: str | None = None
engine: AsyncEngine | None = None
AsyncSessionLocal = async_sessionmaker(
    class_=AsyncSession,
    expire_on_commit=False,
)


def configure_database(database_url: str) -> AsyncEngine:
    """Create and bind the database engine after startup validation succeeds."""

    global DATABASE_URL, engine

    if engine is not None and DATABASE_URL == database_url:
        return engine

    DATABASE_URL = database_url
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
    )
    AsyncSessionLocal.configure(bind=engine)
    return engine


async def dispose_database() -> None:
    """Dispose the configured engine during application shutdown."""

    global DATABASE_URL, engine

    if engine is not None:
        await engine.dispose()
    AsyncSessionLocal.configure(bind=None)
    DATABASE_URL = None
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
