"""Track the existing R2 knowledge administration models used by search ingestion."""
from alembic import op
import sqlalchemy as sa

revision = "20261028_knowledge"
down_revision = "20261028_search_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_document",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("region", sa.String(32), nullable=True),
        sa.Column("source_type", sa.String(32), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("bucket", sa.Text(), nullable=False),
        sa.Column("object_key", sa.Text(), unique=True, nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("etag", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        if_not_exists=True,
    )
    op.create_index("ix_knowledge_document_status", "knowledge_document", ["status"], if_not_exists=True)
    op.create_table(
        "knowledge_upload",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("knowledge_document.id"), nullable=True),
        sa.Column("base_revision", sa.Integer(), nullable=True),
        sa.Column("bucket", sa.Text(), nullable=False),
        sa.Column("parent_prefix", sa.Text(), nullable=False),
        sa.Column("staging_key", sa.Text(), unique=True, nullable=False),
        sa.Column("final_key", sa.Text(), unique=True, nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        if_not_exists=True,
    )


def downgrade() -> None:
    raise RuntimeError("Export and review knowledge documents/uploads before removing storage tables")
