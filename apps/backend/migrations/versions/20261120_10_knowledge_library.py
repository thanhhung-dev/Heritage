"""Durable knowledge library upload sessions; no existing data is modified."""
from alembic import op
import sqlalchemy as sa

revision = "20261120_knowledge_library"
down_revision = "20261120_classification"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "knowledge_library_upload",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.BigInteger(), nullable=False),
        sa.Column("bucket", sa.String(32), nullable=False),
        sa.Column("final_key", sa.Text(), nullable=False),
        sa.Column("reservation_key", sa.Text(), unique=True),
        sa.Column("staging_key", sa.Text(), nullable=False, unique=True),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("final_etag", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("bucket = 'knowledge-heritage'", name="ck_library_bucket"),
        sa.CheckConstraint("size_bytes > 0 AND size_bytes <= 33554432", name="ck_library_size"),
        sa.CheckConstraint("status IN ('PENDING','COMPLETED','EXPIRED','CONFLICT')", name="ck_library_status"),
        sa.CheckConstraint("(status = 'PENDING' AND reservation_key = final_key) OR "
                           "(status <> 'PENDING' AND reservation_key IS NULL)", name="ck_library_reservation"),
        sa.CheckConstraint("status <> 'PENDING' OR reservation_key IS NOT NULL", name="ck_library_pending"),
    )
    op.create_index("ix_library_expiry", "knowledge_library_upload", ["status", "expires_at"])
    op.create_index("ix_knowledge_library_upload_actor_id", "knowledge_library_upload", ["actor_id"])


def downgrade():
    # Do not silently discard recovery records for already published objects.
    raise RuntimeError("Export upload recovery records and retire active sessions before removing this table.")
