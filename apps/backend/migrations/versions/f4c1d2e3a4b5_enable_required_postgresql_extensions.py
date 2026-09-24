"""enable required PostgreSQL extensions

Revision ID: f4c1d2e3a4b5
Revises: d0f4a2c81e7b
Create Date: 2026-09-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f4c1d2e3a4b5"
down_revision: Union[str, Sequence[str], None] = "d0f4a2c81e7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure clean and previously migrated databases have all extensions."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")


def downgrade() -> None:
    """Preserve shared extensions and the database objects using them."""
    # Dropping pg_trgm would break baseline indexes, and extensions may be
    # shared by schemas outside this application. Downgrade only moves the
    # Alembic revision marker; a following upgrade remains idempotent.
    pass
