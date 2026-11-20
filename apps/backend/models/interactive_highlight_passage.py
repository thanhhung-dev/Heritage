"""Reviewed links from tour highlights to OpenSearch passage identities."""
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.db.base import Base


class InteractiveHighlightPassage(Base):
    __tablename__ = "interactive_highlight_passage"

    highlight_id: Mapped[int] = mapped_column(
        ForeignKey("interactive_highlight.id", ondelete="CASCADE"), primary_key=True,
    )
    passage_id: Mapped[str] = mapped_column(String(512), primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    object_key: Mapped[str] = mapped_column(String, nullable=False, default="")
    bucket: Mapped[str] = mapped_column(String, nullable=False, default="")
