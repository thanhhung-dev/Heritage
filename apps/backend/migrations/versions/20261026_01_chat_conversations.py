"""Add account conversations and normalized citations without removing legacy sessions.

This is the first Alembic revision in this checkout. It extends an existing
application database containing account, heritage, chat_session and chat_message;
it is not a replacement for the application's initial schema.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261026_chat"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("account.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("heritage_id", sa.BigInteger(), sa.ForeignKey("heritage.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_conversation_account_updated", "conversation", ["account_id", "updated_at", "id"])
    op.add_column("chat_message", sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.alter_column("chat_message", "session_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.create_foreign_key(
        "fk_chat_message_conversation", "chat_message", "conversation",
        ["conversation_id"], ["id"], ondelete="CASCADE",
    )
    op.create_check_constraint(
        "chk_msg_one_parent", "chat_message",
        "(session_id IS NOT NULL AND conversation_id IS NULL) OR "
        "(session_id IS NULL AND conversation_id IS NOT NULL)",
    )
    op.create_index("idx_msg_conversation_created", "chat_message", ["conversation_id", "created_at", "id"])
    op.create_table(
        "message_citation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_message.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_title", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
    )
    op.create_index("ix_message_citation_message_id", "message_citation", ["message_id"])


def downgrade() -> None:
    # Refuse a rollback that would discard persisted conversation messages/citations.
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM chat_message WHERE conversation_id IS NOT NULL)
             OR EXISTS (SELECT 1 FROM message_citation) THEN
            RAISE EXCEPTION 'Export conversation data before downgrading chat storage';
          END IF;
        END $$;
    """)
    op.drop_index("ix_message_citation_message_id", table_name="message_citation")
    op.drop_table("message_citation")
    op.drop_index("idx_msg_conversation_created", table_name="chat_message")
    op.drop_constraint("chk_msg_one_parent", "chat_message", type_="check")
    op.drop_constraint("fk_chat_message_conversation", "chat_message", type_="foreignkey")
    op.drop_column("chat_message", "conversation_id")
    op.alter_column("chat_message", "session_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.drop_index("idx_conversation_account_updated", table_name="conversation")
    op.drop_table("conversation")
