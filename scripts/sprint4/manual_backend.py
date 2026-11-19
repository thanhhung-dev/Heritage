"""Serve the actual backend with disposable Sprint 4 manual-test data.

Run from the repository root. Ctrl+C stops children and removes only resources
created by this process. --rag additionally creates an owned temporary R2 text
source and OpenSearch index, and starts the production worker. --check exercises
the real HTTP server and exits, including cleanup. Never changes application .env.
"""
import argparse
import asyncio
from contextlib import ExitStack
import os
from pathlib import Path
import secrets
import re
import subprocess
import sys
import time
from uuid import uuid4

from dotenv import dotenv_values
import httpx
import psycopg
from psycopg import sql
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def drop_database(admin_url, database):
    # The name is generated here, never accepted from a CLI/env/file.
    if not re.fullmatch(r"test_sprint4_manual_[0-9a-f]{32}", database):
        raise RuntimeError("Refusing an unowned database name")
    with psycopg.connect(admin_url, autocommit=True, connect_timeout=5) as connection:
        connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))
    print("Owned manual-test database removed.", flush=True)


def seed(database_url, password):
    from apps.backend.core.security import hash_password
    from apps.backend.models.knowledge import KnowledgeDocument, KnowledgeUpload
    from apps.backend.models.revoked_token import RevokedToken

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql((ROOT / "schema.sql").read_text(encoding="utf-8"))
            connection.exec_driver_sql("""CREATE TABLE roles(id BIGINT PRIMARY KEY, name TEXT UNIQUE NOT NULL);
                CREATE TABLE account(id BIGINT PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(255) UNIQUE NOT NULL, password_hash VARCHAR(255) NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE, locked_until TIMESTAMPTZ,
                    role_id BIGINT REFERENCES roles(id), created_by VARCHAR(100), updated_by VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP);
                INSERT INTO roles VALUES(1,'USER'),(2,'ADMIN');""")
            for name in ("2026-11-19_account_token_version.sql", "2026-11-19_rag_pipeline.sql"):
                connection.exec_driver_sql((ROOT / "apps/backend/migrations" / name).read_text(encoding="utf-8"))
            for table in (RevokedToken.__table__, KnowledgeDocument.__table__, KnowledgeUpload.__table__):
                table.create(connection)
            connection.execute(text("""INSERT INTO account(id,email,username,password_hash,role_id,is_active)
                VALUES(1,'admin@example.com','admin',:hash,2,TRUE),
                      (2,'user@example.com','user',:hash,1,TRUE),
                      (3,'disabled@example.com','disabled',:hash,1,FALSE)"""), {"hash": hash_password(password)})
            connection.exec_driver_sql("""INSERT INTO heritage(slug,title,publish_state)
                VALUES('sprint4-test','Sprint 4 test','published'),('foreign-test','Foreign test','draft');
                INSERT INTO sky_preset(name,turbidity,elevation) VALUES('Day',2,45);
                INSERT INTO scene(heritage_id,sequence,title) VALUES
                    (1,-1,'Overview'),(1,0,'First'),(1,1,'Second'),(2,0,'Foreign');
                INSERT INTO model_asset(scene_id,file_url) VALUES
                    (2,'models/camera.glb'),(4,'models/foreign.glb');""")
    finally:
        engine.dispose()


async def search_setup(url, index, stack):
    from urllib.parse import urlsplit
    from apps.backend.core.search import PassageStore
    if urlsplit(url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("Use the explicit loopback verification search cluster")
    async with PassageStore(url=url, index=index) as store:
        cluster = await store._request("GET", "/")
        if cluster.get("cluster_name") != "sprint4-rag-verification":
            raise RuntimeError("This launcher requires the owned sprint4-rag-verification cluster")
        stack.callback(search_cleanup, url, index)
        await store.ensure_index()


def search_cleanup(url, index):
    async def remove():
        from apps.backend.core.search import PassageStore
        async with PassageStore(url=url, index=index) as store:
            for path in (f"/{index}", f"/_search/pipeline/{index}-hybrid"):
                response = await store.client.delete(store.url + path)
                if response.status_code not in {200, 404}:
                    raise RuntimeError("Owned search resource cleanup failed")
    asyncio.run(remove())
    print("Owned manual-test search resources removed.", flush=True)


def source_cleanup(storage, key, owner, etag):
    head = storage.call("head_object", Key=key)
    if head.get("Metadata", {}).get("sprint4-owner") != owner or head["ETag"] != etag:
        raise RuntimeError("Owned R2 source changed; cleanup refused")
    storage.call("delete_object", Key=key, IfMatch=etag)
    from fastapi import HTTPException
    try:
        storage.call("head_object", Key=key)
    except HTTPException as error:
        if error.status_code == 404:
            print("Owned R2 source deleted and HEAD 404 verified.", flush=True)
            return
        raise
    raise RuntimeError("Owned R2 source still exists after deletion")


def prepare_rag(stack, database_url, owner, index):
    from apps.backend.core.r2 import R2Storage, knowledge_prefix
    from apps.backend.models.knowledge import KnowledgeDocument
    search_url = os.environ.get("OPENSEARCH_TEST_URL", "")
    if not search_url:
        raise RuntimeError("--rag requires explicit OPENSEARCH_TEST_URL")
    asyncio.run(search_setup(search_url, index, stack))
    storage = R2Storage()
    stack.callback(storage.client.close)
    key = knowledge_prefix() + f"sprint4-tests/{owner}/manual-pipeline.txt"
    body = ("Sprint 4 pipeline verification document. This is technical test data. " * 8).encode()
    result = storage.call("put_object", Key=key, Body=body, ContentType="text/plain",
                          IfNoneMatch="*", Metadata={"sprint4-owner": owner})
    stack.callback(source_cleanup, storage, key, owner, result["ETag"])
    head = storage.call("head_object", Key=key)
    document_id = str(uuid4())
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(KnowledgeDocument.__table__.insert().values(
                id=document_id, title="Sprint 4 manual test", bucket=storage.bucket, object_key=key,
                filename="manual-pipeline.txt", content_type="text/plain", size_bytes=head["ContentLength"],
                etag=head["ETag"], revision=1, status="uploaded"))
    finally:
        engine.dispose()
    return document_id, search_url


def check_http(base, password, document_id):
    with httpx.Client(base_url=base, timeout=10) as client:
        login = client.post("/api/admin/login", json={"email": "admin@example.com", "password": password})
        login.raise_for_status()
        client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
        assert client.get("/api/admin/heritages/1/scenes").status_code == 200
        saved = client.put("/api/admin/scenes/2/3d-config", json={"camera": {
            "start_position": [1, 2, 3], "start_target": [0, 0, 0]}, "sky_preset_id": 1})
        saved.raise_for_status()
        public = client.get("/api/heritages/sprint4-test")
        public.raise_for_status()
        assert public.json()["scenes"][0]["camera"] == saved.json()["camera"]
        pipeline = client.post("/api/admin/rag/pipelines", json={"name": "HTTP smoke"})
        pipeline.raise_for_status()
        if document_id:
            job = client.post(f'/api/admin/rag/pipelines/{pipeline.json()["id"]}/reindex',
                              json={"document_ids": [document_id]})
            job.raise_for_status()
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                actual = client.get(f'/api/admin/rag/jobs/{job.json()["id"]}')
                actual.raise_for_status()
                if actual.json()["status"] in {"COMPLETED", "FAILED"}:
                    assert actual.json()["status"] == "COMPLETED", actual.json()["error"]
                    assert actual.json()["processed_documents"] == 1
                    assert actual.json()["indexed_passages"] > 0
                    async def verify_vector():
                        from apps.backend.core.search import PassageStore
                        async with PassageStore() as store:
                            result = await store._request("POST", f"/{store.index}/_search", json={
                                "size": 1, "query": {"term": {"document_key": document_id}}})
                            assert result["hits"]["total"]["value"] == actual.json()["indexed_passages"]
                            assert len(result["hits"]["hits"][0]["_source"]["embedding"]) == 1024
                    asyncio.run(verify_vector())
                    print("Real HTTP -> R2 -> BGE-M3 -> OpenSearch job COMPLETED.", flush=True)
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError("Worker did not complete before the verification deadline")
        assert client.post("/api/admin/logout").status_code == 204
        assert client.get("/api/admin/rag/pipelines").status_code == 401
    print("Actual backend HTTP smoke passed.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18004)
    parser.add_argument("--rag", action="store_true", help="Use owned real R2/search resources and start worker")
    parser.add_argument("--check", action="store_true", help="Check actual HTTP flows, clean up and exit")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use an unprivileged port between 1024 and 65535")
    values = {**dotenv_values(ROOT / ".env"), **os.environ}
    url = make_url(values.get("DATABASE_URL", ""))
    if url.drivername != "postgresql+psycopg" or url.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("Configure a loopback postgresql+psycopg DATABASE_URL")
    if args.rag and not values.get("OPENSEARCH_TEST_URL"):
        parser.error("--rag requires explicit OPENSEARCH_TEST_URL before creating resources")
    owner = uuid4().hex
    database, index = "test_sprint4_manual_" + owner, "sprint4-manual-test-" + owner
    admin_url = url.set(drivername="postgresql").render_as_string(hide_password=False)
    test_url = url.set(database=database).render_as_string(hide_password=False)
    password = secrets.token_urlsafe(20)
    os.environ.update({key: str(value) for key, value in values.items() if value is not None})
    os.environ.update({"DATABASE_URL": test_url, "JWT_SECRET_KEY": secrets.token_urlsafe(48),
        "APP_ENVIRONMENT": "test", "JWT_ISSUER": "", "JWT_AUDIENCE": "", "OTEL_TRACING_ENABLED": "false",
        "SMTP_HOST": "", "SMTP_PORT": "", "SMTP_USER": "", "SMTP_PASSWORD": "", "SMTP_SENDER_EMAIL": "",
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "OPENSEARCH_INDEX": index})
    with ExitStack() as stack:
        with psycopg.connect(admin_url, autocommit=True, connect_timeout=5) as connection:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
        stack.callback(drop_database, admin_url, database)
        seed(test_url, password)
        document_id = None
        if args.rag:
            document_id, search_url = prepare_rag(stack, test_url, owner, index)
            os.environ["OPENSEARCH_URL"] = search_url
        environment = dict(os.environ)
        quiet = {"stdout": subprocess.DEVNULL, "stderr": subprocess.STDOUT} if args.check else {}
        base = f"http://127.0.0.1:{args.port}"
        process = subprocess.Popen([sys.executable, "-X", "utf8", "-m", "apps.backend",
            "--host", "127.0.0.1", "--port", str(args.port)],
            cwd=ROOT, env=environment, **quiet)
        stack.callback(stop, process)
        deadline = time.monotonic() + 30
        while True:
            if process.poll() is not None:
                raise RuntimeError("Backend stopped during startup; check configuration/port")
            try:
                if httpx.get(base + "/openapi.json", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            if time.monotonic() > deadline:
                raise RuntimeError("Backend startup deadline exceeded")
            time.sleep(0.25)
        if args.rag:
            worker = subprocess.Popen([sys.executable, "-X", "utf8", "-m", "apps.backend.services.reindex_worker",
                "--poll-seconds", "0.5"], cwd=ROOT, env=environment, **quiet)
            stack.callback(stop, worker)
        if args.check:
            check_http(base, password, document_id)
        else:
            print(f"\nSwagger: {base}/docs\nAdmin: admin@example.com (id=1)\nUser: user@example.com (id=2)\n"
                  f"Disabled: disabled@example.com (id=3)\nPassword for these disposable accounts: {password}\n"
                  f"Heritage=1; overview=1; scenes=2,3; foreign scene=4; assets=1,2; sky=1\n"
                  f"RAG document_id: {document_id or 'not enabled (restart with --rag)'}\n"
                  "Ctrl+C cleans up this sandbox. No application .env was changed.\n", flush=True)
            while process.poll() is None:
                time.sleep(0.5)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Manual sandbox stopped.")
    except httpx.HTTPStatusError as error:
        print(f"HTTP {error.response.status_code} on {error.request.url.path}: {error.response.text[:300]}",
              file=sys.stderr)
        raise SystemExit(1)
    except Exception as error:
        print(f"Manual sandbox failed ({type(error).__name__}); inspect local configuration and cleanup messages.",
              file=sys.stderr)
        raise SystemExit(1)
