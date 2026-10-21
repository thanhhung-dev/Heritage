"""Initialize the PostgreSQL schema directly from the ORM models.

This replaces Alembic. On startup we create only the tables that are missing
(``checkfirst``), add only the columns that are missing, and seed a few
reference rows. Nothing is ever dropped, retyped or narrowed, so existing data
is always preserved. The resulting schema mirrors ``schema.sql`` for the objects
the application actually uses.
"""

from __future__ import annotations

import os


# Business/KG tables only; passage vectors are indexed in OpenSearch.
REQUIRED_EXTENSIONS = ("pgcrypto", "pg_trgm", "unaccent")

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


def _add_missing_columns(engine) -> None:
    """Bù những cột có trong ORM mà bảng đã tồn tại còn thiếu.

    ``create_all(checkfirst=True)`` chỉ tạo bảng THIẾU — nó không bao giờ sửa
    bảng đã có, nên thêm một cột vào model (ví dụ ``interactive.explore_title``)
    sẽ không bao giờ tới được database đang chạy và API sẽ chết với
    "column does not exist". Ở đây chỉ THÊM cột còn thiếu
    (``ADD COLUMN IF NOT EXISTS``): không xoá, không đổi kiểu, không siết ràng
    buộc của cột đã có.
    """
    from sqlalchemy import inspect, text

    from apps.backend.models import Base

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        present = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in present:
                continue
            # Cột NOT NULL không mặc định sẽ làm `ALTER TABLE` thất bại trên bảng
            # đang có dữ liệu — bỏ qua kèm cảnh báo thay vì làm sập khởi động.
            if not column.nullable and column.server_default is None and column.default is None:
                print(
                    f"[init_db] bỏ qua {table.name}.{column.name}: "
                    "NOT NULL không mặc định, cần backfill thủ công"
                )
                continue
            ddl_type = column.type.compile(dialect=engine.dialect)
            with engine.begin() as connection:
                connection.execute(
                    text(
                        f'ALTER TABLE "{table.name}" '
                        f'ADD COLUMN IF NOT EXISTS "{column.name}" {ddl_type}'
                    )
                )
            print(f"[init_db] đã thêm cột {table.name}.{column.name} ({ddl_type})")


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
        _add_missing_columns(engine)

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
