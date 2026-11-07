"""Preserve conversation scope and allow grounded social chat without citations."""
from alembic import op
import sqlalchemy as sa

revision = "20261106_chat_scope"
down_revision = "20261028_account_sequence"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("conversation", sa.Column("active_area_id", sa.String(80), nullable=True))
    op.drop_constraint("chk_msg_citations", "chat_message", type_="check")
    op.create_check_constraint(
        "chk_msg_citations", "chat_message",
        "role = 'user' OR abstained OR jsonb_array_length(citations) > 0 OR "
        "COALESCE(jsonb_extract_path_text(response_metadata, 'answer_type'), '') = 'conversation' OR "
        "COALESCE(jsonb_extract_path_text(response_metadata, 'needs_user_choice'), 'false') = 'true'",
    )


def downgrade():
    raise RuntimeError("Review persisted conversation scope and outcomes before downgrading")
