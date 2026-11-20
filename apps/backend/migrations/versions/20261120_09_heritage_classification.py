"""Editorial classification, transactional SQL outbox and artifact catalog."""
from pathlib import Path

from alembic import op

revision = "20261120_classification"
down_revision = "20261119_highlight_passage"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().exec_driver_sql(Path(__file__).with_suffix(".sql").read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("Export reviewed catalog data before schema removal; use guarded classification rollback for data changes")
