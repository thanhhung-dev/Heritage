"""Run classification integration checks in a new owned local test database."""
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from dotenv import dotenv_values
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


def main():
    values = {**dotenv_values(ROOT / ".env"), **os.environ}
    url = make_url(values.get("DATABASE_URL", ""))
    if url.drivername != "postgresql+psycopg" or url.host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("Configure explicit loopback postgresql+psycopg DATABASE_URL")
    database = "test_catalog_" + uuid4().hex
    admin_url = url.set(drivername="postgresql").render_as_string(hide_password=False)
    environment = {key: str(value) for key, value in values.items() if value is not None}
    environment["CATALOG_TEST_DATABASE_URL"] = url.set(database=database).render_as_string(hide_password=False)
    with psycopg.connect(admin_url, autocommit=True, connect_timeout=5) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    try:
        tests = sys.argv[1:] or ["apps/backend/tests/test_catalog_postgres.py"]
        return subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", *tests, "-q", "--tb=short"],
                              cwd=ROOT, env=environment).returncode
    finally:
        with psycopg.connect(admin_url, autocommit=True, connect_timeout=5) as connection:
            connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))
        print("Owned catalog test database removed; application database unchanged.")


if __name__ == "__main__":
    raise SystemExit(main())
