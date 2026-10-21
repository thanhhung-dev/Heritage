"""ORM entities mapped 1:1 from schema.sql.

Import order matters — các model phụ thuộc theo thứ tự:
  admin → user → kg → heritage → scene/... → chat
"""
from apps.backend.common.db.base import Base, TimestampMixin, AsyncSessionLocal, engine, DATABASE_URL  # noqa: F401

from apps.backend.common.models.admin import AdminAccount, AuditLog  # noqa: F401
from apps.backend.common.models.knowledge import KnowledgeDocument, KnowledgeUpload  # noqa: F401
from apps.backend.common.models.user import Role, Account, UserProfile, UserConsent  # noqa: F401
from apps.backend.common.models.kg import (  # noqa: F401
    CorpusRelease, Document, Passage, Entity, EntityAlias, EntityEvidence,
    EntityAliasEvidence, Predicate, Relation, PlaceLocation,
)
from apps.backend.common.models.heritage import Heritage  # noqa: F401
from apps.backend.common.models.language import Language  # noqa: F401
from apps.backend.common.models.sky_preset import SkyPreset  # noqa: F401
from apps.backend.common.models.scene import Scene  # noqa: F401
from apps.backend.common.models.model_asset import ModelAsset  # noqa: F401
from apps.backend.common.models.voice import Voice  # noqa: F401
from apps.backend.common.models.voice_clip import VoiceClip  # noqa: F401
from apps.backend.common.models.heritage_voice import HeritageVoice  # noqa: F401
from apps.backend.common.models.media_item import MediaItem  # noqa: F401
from apps.backend.common.models.interactive import Interactive  # noqa: F401
from apps.backend.common.models.interactive_highlight import InteractiveHighlight  # noqa: F401
from apps.backend.common.models.scene_highlight import SceneHighlight  # noqa: F401
from apps.backend.common.models.chat import ChatSession, ChatMessage, ChatFeedback  # noqa: F401
from apps.backend.common.models.admin import _uuid_pk as uuid_pk  # noqa: F401

__all__ = [
    # base
    "Base", "TimestampMixin", "AsyncSessionLocal", "engine", "DATABASE_URL",
    "uuid_pk",
    # admin
    "AdminAccount", "AuditLog", "KnowledgeDocument", "KnowledgeUpload",
    # user auth
    "Role", "Account", "UserProfile", "UserConsent",
    # kg
    "CorpusRelease", "Document", "Passage", "Entity", "EntityAlias",
    "EntityEvidence", "EntityAliasEvidence", "Predicate", "Relation", "PlaceLocation",
    # heritage
    "Heritage", "Language",
    # scene graph
    "SkyPreset", "Scene", "ModelAsset",
    "Voice", "VoiceClip", "HeritageVoice",
    "MediaItem",
    "Interactive", "InteractiveHighlight", "SceneHighlight",
    # chat
    "ChatSession", "ChatMessage", "ChatFeedback",
]
