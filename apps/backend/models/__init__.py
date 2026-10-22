"""ORM entities mapped 1:1 from schema.sql.

Import order matters — các model phụ thuộc theo thứ tự:
  admin → user → kg → heritage → scene/... → chat
"""
from apps.backend.db.base import Base, TimestampMixin, AsyncSessionLocal, engine, DATABASE_URL  # noqa: F401

from apps.backend.models.admin import AdminAccount  # noqa: F401
from apps.backend.models.user import (  # noqa: F401
    UserProfile, UserConsent,
    BadgeDefinition, UserBadge,
    MilestoneLevelDefinition, MilestoneTaskDefinition, UserMilestoneTask,
)
from apps.backend.models.kg import (  # noqa: F401
    CorpusRelease, Document, Passage, Entity, EntityAlias, EntityEvidence,
    EntityAliasEvidence, Predicate, Relation, PlaceLocation,
)
from apps.backend.models.heritage import Heritage  # noqa: F401
from apps.backend.models.language import Language  # noqa: F401
from apps.backend.models.sky_preset import SkyPreset  # noqa: F401
from apps.backend.models.scene import Scene  # noqa: F401
from apps.backend.models.model_asset import ModelAsset  # noqa: F401
from apps.backend.models.voice import Voice  # noqa: F401
from apps.backend.models.voice_clip import VoiceClip  # noqa: F401
from apps.backend.models.heritage_voice import HeritageVoice  # noqa: F401
from apps.backend.models.media_item import MediaItem  # noqa: F401
from apps.backend.models.interactive import Interactive  # noqa: F401
from apps.backend.models.interactive_highlight import InteractiveHighlight  # noqa: F401
from apps.backend.models.scene_highlight import SceneHighlight  # noqa: F401
from apps.backend.models.chat import ChatSession, ChatMessage, ChatFeedback  # noqa: F401

__all__ = [
    # base
    "Base", "TimestampMixin", "AsyncSessionLocal", "engine", "DATABASE_URL",
    # admin / identity
    "AdminAccount",
    # profile & gamification
    "UserProfile", "UserConsent",
    "BadgeDefinition", "UserBadge",
    "MilestoneLevelDefinition", "MilestoneTaskDefinition", "UserMilestoneTask",
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

