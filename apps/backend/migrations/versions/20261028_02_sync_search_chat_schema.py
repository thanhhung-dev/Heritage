"""Track merged nullable account and heritage scene fields in Alembic.

Reconcile databases that already ran the standalone camera/sky SQL scripts as
well as databases that only applied the chat revision. Existing values remain.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261028_search_sync"
down_revision = "20261026_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    additions = {
        "account": [("created_by", sa.String(100)), ("updated_by", sa.String(100))],
        "scene": [("camera_path_url", sa.Text())],
        "sky_preset": [
            ("mie_coefficient", sa.Float()), ("mie_directional_g", sa.Float()),
            ("cloud_coverage", sa.Float()), ("cloud_density", sa.Float()), ("stars", sa.Float()),
        ],
        "interactive": [("explore_title", sa.Text()), ("explore_description", sa.Text())],
    }
    for table, columns in additions.items():
        for name, column_type in columns:
            # IF NOT EXISTS also supports schemas updated by the earlier SQL scripts.
            op.add_column(table, sa.Column(name, column_type, nullable=True), if_not_exists=True)


def downgrade() -> None:
    # Columns may predate this revision and contain authored tour/account data.
    raise RuntimeError("Export and review field data before rolling back the merged schema")
