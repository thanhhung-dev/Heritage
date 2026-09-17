"""ORM entities mapped 1:1 from schema.sql.

Import order matters — các model phụ thuộc theo thứ tự:
  admin → kg → content → tour, chat
"""
from backend.db.base import Base, TimestampMixin, AsyncSessionLocal, engine, DATABASE_URL  # noqa: F401

from backend.models.admin import AdminAccount, AuditLog  # noqa: F401
from backend.models.kg import (  # noqa: F401
    Document, Passage, Entity, EntityAlias, Predicate, Relation, PlaceLocation,
)
from backend.models.content import Site, Scene, ModelAsset, RawAsset  # noqa: F401
from backend.models.tour import (  # noqa: F401
    Tour, Story, Narration, Transcript, Highlight, Citation, TourStop,
)
from backend.models.chat import ChatSession, ChatMessage, ChatFeedback  # noqa: F401
from backend.models.admin import _uuid_pk as uuid_pk  # noqa: F401

__all__ = [
    # base
    "Base", "TimestampMixin", "AsyncSessionLocal", "engine", "DATABASE_URL",
    "uuid_pk",
    # admin
    "AdminAccount", "AuditLog",
    # kg
    "Document", "Passage", "Entity", "EntityAlias", "Predicate", "Relation", "PlaceLocation",
    # content
    "Site", "Scene", "ModelAsset", "RawAsset",
    # tour
    "Tour", "Story", "Narration", "Transcript", "Highlight", "Citation", "TourStop",
    # chat
    "ChatSession", "ChatMessage", "ChatFeedback",
]
