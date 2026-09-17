"""Run Alembic migrations and safely adopt the known pre-Alembic schema."""

from __future__ import annotations

import os


BASELINE_REVISION = "b6e199de17dd"
LEGACY_VIEW = "v_tour_stop"
BASELINE_TABLES = frozenset(
    {
        "admin_account",
        "audit_log",
        "chat_feedback",
        "chat_message",
        "chat_session",
        "citation",
        "document",
        "entity",
        "entity_alias",
        "highlight",
        "model_asset",
        "narration",
        "passage",
        "predicate",
        "raw_asset",
        "relation",
        "scene",
        "site",
        "story",
        "tour",
        "transcript",
    }
)


def classify_unversioned_schema(tables: set[str], views: set[str]) -> str:
    """Classify only schemas that are safe to initialize or stamp."""
    application_tables = tables - {"alembic_version"}
    if not application_tables and not views:
        return "empty"

    expected_tables = (BASELINE_TABLES, BASELINE_TABLES | {"place_location"})
    if application_tables in expected_tables and views == {LEGACY_VIEW}:
        return "legacy"

    missing = sorted(BASELINE_TABLES - application_tables)
    unexpected = sorted(application_tables - BASELINE_TABLES - {"place_location"})
    raise ValueError(
        "Unsupported unversioned schema; refusing to stamp it blindly. "
        f"Missing tables: {missing or 'none'}; "
        f"unexpected tables: {unexpected or 'none'}; views: {sorted(views)}"
    )


def _database_objects(database_url: str) -> tuple[set[str], set[str], bool]:
    import psycopg
    from sqlalchemy.engine import make_url

    url = make_url(database_url)
    with psycopg.connect(
        dbname=url.database,
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
            tables = {row[0] for row in cursor.fetchall()}
            cursor.execute(
                "SELECT viewname FROM pg_views WHERE schemaname = 'public'"
            )
            views = {row[0] for row in cursor.fetchall()}

            has_version = False
            if "alembic_version" in tables:
                cursor.execute("SELECT 1 FROM alembic_version LIMIT 1")
                has_version = cursor.fetchone() is not None

    return tables, views, has_version


def main() -> None:
    from alembic import command
    from alembic.config import Config

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    tables, views, has_version = _database_objects(database_url)
    config = Config("alembic.ini")

    if not has_version:
        schema_kind = classify_unversioned_schema(tables, views)
        if schema_kind == "legacy":
            print(f"Adopting recognized legacy schema at revision {BASELINE_REVISION}")
            command.stamp(config, BASELINE_REVISION)

    command.upgrade(config, "head")


if __name__ == "__main__":
    main()
