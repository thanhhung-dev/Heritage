from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.db.base import Base


class HeritageVoice(Base):
    """heritage_voice — junction table linking Heritage ↔ Voice (many-to-many).

    Mirrors schema.sql `heritage_voice`: composite primary key on
    (heritage_id, voice_id) plus a per-heritage sort_order for ordering.
    """

    __tablename__ = "heritage_voice"

    heritage_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("heritage.id", ondelete="CASCADE"),
        primary_key=True,
    )

    voice_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("voice.id", ondelete="CASCADE"),
        primary_key=True,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )