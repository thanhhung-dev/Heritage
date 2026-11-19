"""Add stable editorial identity to interactive highlights."""
from alembic import op
import sqlalchemy as sa

revision = "20261116_artifact_key"
down_revision = "20261106_chat_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interactive_highlight",
        sa.Column("artifact_key", sa.String(length=120), nullable=True),
    )
    op.create_check_constraint(
        "ck_interactive_highlight_artifact_key",
        "interactive_highlight",
        "artifact_key IS NULL OR artifact_key ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'",
    )
    op.create_index(
        "uq_interactive_highlight_artifact_key",
        "interactive_highlight",
        ["artifact_key"],
        unique=True,
        postgresql_where=sa.text("artifact_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_interactive_highlight_artifact_key", table_name="interactive_highlight")
    op.drop_constraint(
        "ck_interactive_highlight_artifact_key",
        "interactive_highlight",
        type_="check",
    )
    op.drop_column("interactive_highlight", "artifact_key")
