"""Initialize the PostgreSQL schema directly from the ORM models.

This replaces Alembic. On startup we create only the tables that are missing
(``checkfirst``) and seed a few reference rows. Nothing is ever dropped or
altered, so existing data is always preserved. The resulting schema mirrors
``schema.sql`` for the objects the application actually uses.
"""

from __future__ import annotations

import os


# gen_random_uuid() (pgcrypto) plus the trigram/unaccent functions used by the
# KG retrieval service, and pgvector for future embedding columns.
REQUIRED_EXTENSIONS = ("pgcrypto", "vector", "pg_trgm", "unaccent")

SEED_STATEMENTS = (
    "INSERT INTO corpus_release(version) VALUES (1) ON CONFLICT DO NOTHING",
)

# Mirrors the predicate seed block in schema.sql.
PREDICATE_SEED = (
    ("founded", "khởi lập", "founded", False),
    ("located_in", "nằm tại", "located in", False),
    ("built_by", "được xây dựng bởi", "built by", False),
    ("restored_by", "được trùng tu bởi", "restored by", False),
    ("designed_by", "được thiết kế bởi", "designed by", False),
    ("associated_with", "liên quan đến", "associated with", True),
    ("part_of", "thuộc về", "part of", False),
    ("contains", "chứa", "contains", False),
    ("commemorates", "tưởng niệm", "commemorates", False),
)


def ensure_schema(database_url: str) -> None:
    """Create missing tables and reference rows. Safe to run repeatedly."""
    from sqlalchemy import create_engine, pool, text
    from apps.backend.models import Base

    engine = create_engine(database_url, poolclass=pool.NullPool)
    try:
        with engine.begin() as connection:
            for extension in REQUIRED_EXTENSIONS:
                connection.execute(
                    text(f'CREATE EXTENSION IF NOT EXISTS "{extension}"')
                )

        Base.metadata.create_all(engine, checkfirst=True)

        with engine.begin() as connection:
            for statement in SEED_STATEMENTS:
                connection.execute(text(statement))
            connection.execute(
                text(
                    "INSERT INTO predicate(code, label_vi, label_en, is_symmetric) "
                    "VALUES (:code, :label_vi, :label_en, :is_symmetric) "
                    "ON CONFLICT (code) DO NOTHING"
                ),
                [
                    {
                        "code": code,
                        "label_vi": label_vi,
                        "label_en": label_en,
                        "is_symmetric": is_symmetric,
                    }
                    for code, label_vi, label_en, is_symmetric in PREDICATE_SEED
                ],
            )
    finally:
        engine.dispose()


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    print("Initializing database schema from ORM models (idempotent)")
    ensure_schema(database_url)
    print("Database schema is up to date")


if __name__ == "__main__":
    main()
