"""repair legacy databases missing place_location

Revision ID: d0f4a2c81e7b
Revises: b6e199de17dd
Create Date: 2026-09-11 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d0f4a2c81e7b"
down_revision: Union[str, Sequence[str], None] = "b6e199de17dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the evidence-backed location table absent from legacy volumes."""
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("place_location"):
        return

    op.create_table(
        "place_location",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("ward", sa.Text(), nullable=True),
        sa.Column("district", sa.Text(), nullable=True),
        sa.Column("province", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_title", sa.Text(), nullable=True),
        sa.Column("source_sentence", sa.Text(), nullable=False),
        sa.Column(
            "verification_status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
            comment="pending | verified | rejected | withdrawn",
        ),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "verification_status IN ('pending', 'verified', 'rejected', 'withdrawn')",
            name="chk_ploc_status",
        ),
        sa.CheckConstraint(
            "latitude IS NULL OR latitude BETWEEN -90 AND 90",
            name="chk_ploc_lat",
        ),
        sa.CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180",
            name="chk_ploc_lng",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="chk_ploc_valid_range",
        ),
        sa.ForeignKeyConstraint(["entity_id"], ["entity.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ploc_entity", "place_location", ["entity_id"])
    op.create_index("ix_ploc_verified", "place_location", ["verification_status"])


def downgrade() -> None:
    """The baseline revision also owns this table, so preserve it."""
    pass
