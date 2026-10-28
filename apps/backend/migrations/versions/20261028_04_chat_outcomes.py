"""Persist clarification and abstention outcomes for complete history restoration."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261028_chat_outcomes"
down_revision = "20261028_knowledge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_message", sa.Column(
        "response_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"),
    ))
    op.drop_constraint("chk_msg_citations", "chat_message", type_="check")
    op.create_check_constraint(
        "chk_msg_citations", "chat_message",
        "role = 'user' OR abstained OR jsonb_array_length(citations) > 0 OR "
        "COALESCE(jsonb_extract_path_text(response_metadata, 'needs_user_choice'), 'false') = 'true'",
    )


def downgrade() -> None:
    raise RuntimeError("Export and review chat outcome metadata before downgrading")
