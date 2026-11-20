"""Run the actual API/worker against owned disposable catalog data.

Default: empty catalog. --fixtures adds explicitly labeled synthetic UI fixtures
only to the new test database. --check validates the real HTTP flow and exits.
Ctrl+C cleans up children and the owned database. No application .env changes.
"""
import argparse
import asyncio
from contextlib import ExitStack
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from uuid import uuid4

from dotenv import dotenv_values
import httpx
import psycopg
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def drop_database(admin_url, name):
    with psycopg.connect(admin_url, autocommit=True, connect_timeout=5) as connection:
        connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
    print("Owned catalog preview database removed.", flush=True)


def prepare(url, fixtures):
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql((ROOT / "schema.sql").read_text(encoding="utf-8"))
            connection.exec_driver_sql("""CREATE TABLE entity(id UUID PRIMARY KEY,name TEXT,type TEXT,summary TEXT,
                entry_status TEXT,source_document_id UUID,source_passage_id UUID)""")
            from apps.backend.models.knowledge import KnowledgeDocument
            KnowledgeDocument.__table__.create(connection)
            connection.exec_driver_sql((ROOT / "apps/backend/migrations/versions/20261120_09_heritage_classification.sql").read_text(encoding="utf-8"))
            if fixtures:
                connection.exec_driver_sql("""INSERT INTO heritage(slug,title,description,publish_state,card_image_url)
                    VALUES('catalog-ui-fixture','Danh thắng kiểm thử','Dữ liệu kiểm thử giao diện; không phải tư liệu lịch sử.','published','/favicon.ico');
                    INSERT INTO heritage_content(slug,title,description,publish_state,card_image_url,entity_type_hint,source_url)
                    VALUES('artifact-ui-fixture','Cổ vật kiểm thử','Dữ liệu kiểm thử giao diện; không phải tư liệu lịch sử.','published','/favicon.ico','artifact','https://example.org/test-fixture'),
                    ('festival-ui-fixture','Lễ hội kiểm thử','Dữ liệu kiểm thử giao diện; không phải tư liệu lịch sử.','published','/favicon.ico','event','https://example.org/test-fixture');""")
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--port", type=int, default=18008)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use a port in [1024,65535]")
    values = {**dotenv_values(ROOT / ".env"), **os.environ}
    url = make_url(values.get("DATABASE_URL", ""))
    if url.drivername != "postgresql+psycopg" or url.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("An explicit loopback postgresql+psycopg connection is required")
    name = "test_catalog_preview_" + uuid4().hex
    admin_url = url.set(drivername="postgresql").render_as_string(hide_password=False)
    test_url = url.set(database=name).render_as_string(hide_password=False)
    runtime = ROOT.parent / ".catalog-test-runtime"
    runtime.mkdir(exist_ok=True)
    environment = {key: str(value) for key, value in values.items() if value is not None}
    environment.update({"DATABASE_URL": test_url, "JWT_SECRET_KEY": secrets.token_urlsafe(48),
        "APP_ENVIRONMENT": "test", "OTEL_TRACING_ENABLED": "false", "HERITAGE_CLASSIFICATION_USE_LLM": "false",
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "EMBEDDING_DEVICE": "cpu",
        "OMP_NUM_THREADS": "4", "MKL_NUM_THREADS": "4", "R2_PUBLIC_BASE_URL": "", "R2_ALLOWED_ASSET_HOSTS": "",
        "SMTP_HOST": "", "SMTP_USER": "", "SMTP_PASSWORD": "", "SMTP_SENDER_EMAIL": "",
        "CORS_ORIGINS": "http://127.0.0.1:3006,http://localhost:3006"})
    with ExitStack() as stack:
        with psycopg.connect(admin_url, autocommit=True, connect_timeout=5) as connection:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        stack.callback(drop_database, admin_url, name)
        prepare(test_url, args.fixtures)
        output = stack.enter_context((runtime / "preview-processes.log").open("w", encoding="utf-8"))
        flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
        for command in (["scripts/run-backend.py", "--port", str(args.port)],
                        ["-m", "apps.backend.services.classification_worker", "--poll-seconds", "0.25"]):
            process = subprocess.Popen([sys.executable, "-X", "utf8", *command], cwd=ROOT, env=environment,
                                       stdout=output, stderr=subprocess.STDOUT, **flags)
            stack.callback(stop, process)
        base = f"http://127.0.0.1:{args.port}"
        deadline = time.monotonic() + 120
        while True:
            try:
                response = httpx.get(base + "/api/catalog/sections", timeout=2)
                if response.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            if time.monotonic() > deadline:
                raise RuntimeError("Preview startup deadline exceeded; inspect preview-processes.log")
            time.sleep(0.5)
        if args.check:
            sections = response.json()
            if args.fixtures:
                assert [row["title"] for row in sections["artifact_collection"]["items"]] == ["Cổ vật kiểm thử"]
                assert [row["title"] for row in sections["festivals_practices"]["items"]] == ["Lễ hội kiểm thử"]
                assert httpx.get(base + "/api/catalog/contents/artifact-ui-fixture").status_code == 200
            else:
                assert all(not page["items"] for page in sections.values())
            print("Actual API and separate worker HTTP preview check passed.", flush=True)
        else:
            print(f"Catalog preview API: {base}/docs; Ctrl+C cleans up. Synthetic fixtures: {args.fixtures}", flush=True)
            while True:
                time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Catalog preview stopped.")
