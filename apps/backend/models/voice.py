from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.db.base import Base

class Voice(Base):
    __tablename__ = "voice"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    heritage_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("heritage.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    headshot_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    intro_video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    heritage: Mapped["Heritage"] = relationship(back_populates="voices")