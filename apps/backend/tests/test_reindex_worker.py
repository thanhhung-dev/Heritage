"""Real queue/chunk/import orchestration; R2, model and search are test adapters."""
import asyncio
import io
import unittest

from apps.backend.services.reindex_worker import run_next
from apps.backend.tests import test_rag_pipeline_api as fixtures


class Storage:
    bucket = "test-bucket"
    body = b"Heritage history and documented architecture. " * 2

    def call(self, method, **kwargs):
        assert method == "get_object" and kwargs["IfMatch"] == "etag"
        return {"Body": io.BytesIO(self.body), "ContentLength": len(self.body)}


class Search:
    def __init__(self):
        self.rows, self.pruned = [], []

    async def ensure_index(self):
        pass

    async def index_passages(self, rows):
        self.rows.extend(rows)

    async def prune_source(self, key, bucket, ids):
        self.pruned.append((key, bucket, ids))


class ReindexWorkerTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.PipelineApiTests.setUpClass.__func__)
    setUp = fixtures.PipelineApiTests.setUp
    create_database = fixtures.PipelineApiTests.create_database
    sql = fixtures.PipelineApiTests.sql
    login = fixtures.PipelineApiTests.login
    headers = staticmethod(fixtures.PipelineApiTests.headers)
    pipeline = fixtures.PipelineApiTests.pipeline

    def schedule(self):
        self.sql("UPDATE knowledge_document SET size_bytes=:size", {"size": len(Storage.body)})
        pipeline = self.pipeline()
        result = self.client.post(f'/api/admin/rag/pipelines/{pipeline["id"]}/reindex',
                                 json={"document_ids": [self.document_id]})
        self.assertEqual(result.status_code, 202, result.text)
        return result.json()

    def job(self, job_id):
        return self.client.get(f"/api/admin/rag/jobs/{job_id}").json()

    @staticmethod
    def vectors(texts):
        return [[1.0] + [0.0] * 1023 for _ in texts]

    def test_real_worker_completion_and_persisted_counts(self):
        job, search = self.schedule(), Search()
        self.assertTrue(asyncio.run(run_next(self.factory, storage=Storage(), store=search, embedder=self.vectors)))
        result = self.job(job["id"])
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["processed_documents"], 1)
        self.assertEqual(result["indexed_passages"], len(search.rows))
        self.assertGreater(len(search.rows), 0)
        self.assertIsNotNone(result["started_at"])
        self.assertIsNotNone(result["finished_at"])
        self.assertEqual(search.pruned[0][0:2], ("knowledge/history.txt", "test-bucket"))
        self.assertFalse(asyncio.run(run_next(self.factory, storage=Storage(), store=search)))

    def test_worker_failure_has_no_fake_success_or_private_error(self):
        job, search = self.schedule(), Search()
        def fail(texts):
            raise RuntimeError("secret-password https://private.example")
        asyncio.run(run_next(self.factory, storage=Storage(), store=search, embedder=fail))
        result = self.job(job["id"])
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["indexed_passages"], 0)
        self.assertEqual(search.pruned, [])
        self.assertNotIn("secret-password", result["error"])
        self.assertIsNone(self.sql("SELECT active_slot FROM rag_reindex_job")[0][0])

    def test_changed_document_is_rejected(self):
        job = self.schedule()
        self.sql("UPDATE knowledge_document SET revision=2")
        search = Search()
        asyncio.run(run_next(self.factory, storage=Storage(), store=search, embedder=self.vectors))
        self.assertEqual(self.job(job["id"])["status"], "FAILED")
        self.assertEqual(search.rows, [])

    def test_disabled_requester_cannot_start_queued_writes(self):
        job, search = self.schedule(), Search()
        self.sql("UPDATE account SET is_active=0 WHERE id=1")
        asyncio.run(run_next(self.factory, storage=Storage(), store=search, embedder=self.vectors))
        self.assertEqual(self.sql("SELECT status FROM rag_reindex_job WHERE id=:id", {"id": job["id"]})[0][0],
                         "FAILED")
        self.assertEqual(search.rows, [])

    def test_two_workers_claim_a_job_only_once(self):
        job, search = self.schedule(), Search()
        async def compete():
            return await asyncio.gather(*[run_next(self.factory, storage=Storage(), store=search,
                                                 embedder=self.vectors) for _ in range(2)])
        claimed = asyncio.run(compete())
        self.assertEqual(sum(claimed), 1)
        self.assertEqual(self.job(job["id"])["status"], "COMPLETED")
        self.assertEqual(len(search.pruned), 1)
