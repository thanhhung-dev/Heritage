from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column


class Heritage(Base):
    __tablename__ = "heritage"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)

    tagline: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    region: Mapped[str | None] = mapped_column(Text, nullable=True)

    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    launch_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    publish_state: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    publish_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    headline: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    map_zoom: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    hover_video_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    community_made: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    presented_by_logo_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    display_map: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    splash_image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    card_image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    language1_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    language2_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )