"""Pipeline and queue HTTP contracts with real auth and isolated database writes."""
import asyncio
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from unittest.mock import patch

from apps.backend.api.admin import rag
from apps.backend.core import security
from apps.backend.models.knowledge import KnowledgeDocument
from apps.backend.models.rag_pipeline import RagPipeline, ReindexJob
from apps.backend.tests import test_admin_auth as fixtures


class PipelineApiTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.AdminAuthTests.setUpClass.__func__)
    create_database = fixtures.AdminAuthTests.create_database
    sql = fixtures.AdminAuthTests.sql
    login = fixtures.AdminAuthTests.login
    headers = staticmethod(fixtures.AdminAuthTests.headers)

    def setUp(self):
        fixtures.AdminAuthTests.setUp(self)
        self.enterContext(patch.dict(os.environ, {"R2_BUCKET": "test-bucket", "R2_KNOWLEDGE_PREFIX": "knowledge/"}))
        async def create():
            async with self.engine.begin() as conn:
                for table in (KnowledgeDocument.__table__, RagPipeline.__table__, ReindexJob.__table__):
                    await conn.run_sync(table.create)
        asyncio.run(create())
        self.app.include_router(rag.router)
        self.client.headers.update(self.headers(self.login().json()["access_token"]))
        self.document_id = str(uuid4())
        self.sql("""INSERT INTO knowledge_document
            (id,title,bucket,object_key,filename,content_type,size_bytes,etag,revision,status,created_at,updated_at)
            VALUES (:id,'History','test-bucket','knowledge/history.txt','history.txt','text/plain',50,'etag',1,
                    'uploaded',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)""", {"id": self.document_id})

    def pipeline(self, name="Heritage"):
        response = self.client.post("/api/admin/rag/pipelines", json={"name": name})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_crud_and_optimistic_revision(self):
        row = self.pipeline()
        url = f'/api/admin/rag/pipelines/{row["id"]}'
        self.assertEqual(self.client.get(url).json(), row)
        response = self.client.patch(url, json={"expected_revision": 1, "retrieval": {"top_k": 15}})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["revision"], 2)
        self.assertEqual(response.json()["retrieval"]["top_k"], 15)
        self.assertEqual(self.client.patch(url, json={"expected_revision": 1, "name": "Stale"}).status_code, 409)
        self.assertEqual(self.client.post("/api/admin/rag/pipelines", json={"name": "Heritage"}).status_code, 409)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_cursor_pagination(self):
        for name in ("One", "Two", "Three"):
            self.pipeline(name)
        first = self.client.get("/api/admin/rag/pipelines?limit=2").json()
        second = self.client.get("/api/admin/rag/pipelines", params={"limit": 2, "cursor": first["next_cursor"]}).json()
        self.assertEqual(len(first["items"]), 2)
        self.assertEqual(len(second["items"]), 1)
        self.assertIsNone(second["next_cursor"])
        self.assertEqual(len({r["id"] for r in first["items"] + second["items"]}), 3)

    def test_duplicate_rename_is_a_conflict_and_preserves_revision(self):
        first, second = self.pipeline("First"), self.pipeline("Second")
        url = f'/api/admin/rag/pipelines/{second["id"]}'
        result = self.client.patch(url, json={"expected_revision": 1, "name": first["name"]})
        self.assertEqual(result.status_code, 409, result.text)
        unchanged = self.client.get(url).json()
        self.assertEqual(unchanged["name"], "Second")
        self.assertEqual(unchanged["revision"], 1)

    def test_job_is_durable_scoped_and_duplicate_safe(self):
        row = self.pipeline()
        url = f'/api/admin/rag/pipelines/{row["id"]}'
        response = self.client.post(url + "/reindex", json={"document_ids": [self.document_id]})
        self.assertEqual(response.status_code, 202, response.text)
        job = response.json()
        self.assertEqual(job["status"], "PENDING")
        self.assertEqual(job["processed_documents"], 0)
        self.assertIsNone(job["started_at"])
        self.assertNotIn("config_snapshot", job)
        self.assertEqual(self.client.get(f'/api/admin/rag/jobs/{job["id"]}').json(), job)
        self.assertEqual(self.client.post(url + "/reindex", json={"document_ids": [self.document_id]}).status_code, 409)
        self.assertEqual(self.client.patch(url, json={"expected_revision": 1, "name": "Busy"}).status_code, 409)
        self.assertEqual(self.client.delete(url).status_code, 409)

    def test_job_scope_and_configuration_validation(self):
        row = self.pipeline()
        url = f'/api/admin/rag/pipelines/{row["id"]}/reindex'
        self.assertEqual(self.client.post(url, json={"document_ids": [str(uuid4())]}).status_code, 404)
        self.sql("UPDATE knowledge_document SET bucket='other'")
        self.assertEqual(self.client.post(url, json={"document_ids": [self.document_id]}).status_code, 409)
        self.sql("UPDATE knowledge_document SET bucket='test-bucket', object_key='outside/history.txt'")
        self.assertEqual(self.client.post(url, json={"document_ids": [self.document_id]}).status_code, 422)
        self.assertEqual(self.client.get(f"/api/admin/rag/jobs/{uuid4()}").status_code, 404)
        self.assertEqual(self.client.post("/api/admin/rag/pipelines", json={"name": "Invalid", "retrieval": {"top_k": 101}}).status_code, 422)

    def test_simultaneous_reindex_triggers_persist_only_one_active_job(self):
        row = self.pipeline()
        url = f'/api/admin/rag/pipelines/{row["id"]}/reindex'
        def trigger(_):
            return self.client.post(url, json={"document_ids": [self.document_id]}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(trigger, range(2)))
        self.assertEqual(sorted(results), [202, 409])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM rag_reindex_job WHERE active_slot=1")[0][0], 1)

    def test_every_operation_requires_current_admin(self):
        pipeline_id, job_id = uuid4(), uuid4()
        operations = [("post", "/pipelines"), ("get", "/pipelines"),
                      ("get", f"/pipelines/{pipeline_id}"), ("patch", f"/pipelines/{pipeline_id}"),
                      ("delete", f"/pipelines/{pipeline_id}"), ("post", f"/pipelines/{pipeline_id}/reindex"),
                      ("get", f"/jobs/{job_id}")]
        self.client.headers.pop("Authorization")
        for method, suffix in operations:
            self.assertEqual(getattr(self.client, method)("/api/admin/rag" + suffix).status_code, 401)
        self.client.headers.update(self.headers(security.create_access_token({"sub": "2", "role": "admin"})))
        for method, suffix in operations:
            self.assertEqual(getattr(self.client, method)("/api/admin/rag" + suffix).status_code, 403)
