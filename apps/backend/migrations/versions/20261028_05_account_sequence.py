"""Align the existing account sequence after legacy MAX(id)+1 registrations."""
from alembic import op

revision = "20261028_account_sequence"
down_revision = "20261028_chat_outcomes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Take the same table lock as INSERT while repairing the allocator. The
    # sequence never moves backwards and no account rows or IDs are rewritten.
    op.execute("LOCK TABLE account IN SHARE ROW EXCLUSIVE MODE")
    op.execute("""
        DO $$
        DECLARE
            allocator regclass;
            sequence_value bigint;
            account_max bigint;
        BEGIN
            allocator := pg_get_serial_sequence('account', 'id')::regclass;
            IF allocator IS NULL THEN
                RAISE EXCEPTION 'account.id must have a database sequence';
            END IF;
            EXECUTE format('SELECT last_value FROM %s', allocator) INTO sequence_value;
            SELECT COALESCE(MAX(id), 0) INTO account_max FROM account;
            PERFORM setval(allocator, GREATEST(sequence_value, account_max, 1), true);
        END $$;
    """)


def downgrade() -> None:
    # Rewinding an allocator could duplicate an existing account ID.
    pass
