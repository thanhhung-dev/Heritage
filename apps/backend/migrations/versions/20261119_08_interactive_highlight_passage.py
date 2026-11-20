"""Link reviewed highlight identities to versioned OpenSearch passages."""
from alembic import op
import sqlalchemy as sa

revision = "20261119_highlight_passage"
down_revision = "20261116_artifact_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interactive_highlight_passage",
        sa.Column("highlight_id", sa.Integer(), sa.ForeignKey("interactive_highlight.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("passage_id", sa.String(length=512), primary_key=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("object_key", sa.String(), nullable=False, server_default=""),
        sa.Column("bucket", sa.String(), nullable=False, server_default=""),
        sa.CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="ck_highlight_passage_hash"),
    )


def downgrade() -> None:
    op.drop_table("interactive_highlight_passage")
