"""Live PostgreSQL queue integration; S3/search/model boundaries are explicit test adapters."""
import asyncio
import io
import json
import os
import unittest
from uuid import uuid4
from unittest.mock import patch

import boto3
from botocore.response import StreamingBody
from botocore.stub import Stubber
from fastapi import HTTPException
import httpx
from sqlalchemy import select, text

from apps.backend.core.r2 import R2Storage
from apps.backend.core.search import PassageStore
from apps.backend.models.knowledge import KnowledgeDocument
from apps.backend.models.rag_pipeline import ReindexJob
from apps.backend.schemas.rag_pipeline import PipelineCreate
from apps.backend.services.rag_pipeline import PipelineService
from apps.backend.services.reindex_worker import run_next
from apps.backend.tests import test_sprint4_postgres as fixtures


@unittest.skipUnless(os.environ.get('SPRINT4_POSTGRES_TEST_URL'), 'explicit disposable PostgreSQL test database required')
class RagPostgresTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(fixtures.Sprint4PostgresTests.setUpClass.__func__)
    drop_schema = fixtures.Sprint4PostgresTests.drop_schema

    async def asyncSetUp(self):
        await fixtures.Sprint4PostgresTests.asyncSetUp(self)
        self.enterContext(patch.dict(os.environ, {'R2_BUCKET': 'test-bucket', 'R2_KNOWLEDGE_PREFIX': 'curated/'}))
        self.source_id = str(uuid4())
        self.body = b'Heritage history, architecture and cultural evidence. ' * 4
        async with self.engine.begin() as conn:
            await conn.execute(text('CREATE TABLE roles(id INTEGER PRIMARY KEY, name TEXT NOT NULL)'))
            await conn.execute(text("""ALTER TABLE account
                ADD COLUMN email TEXT, ADD COLUMN username TEXT, ADD COLUMN password_hash TEXT,
                ADD COLUMN locked_until TIMESTAMPTZ, ADD COLUMN role_id INTEGER REFERENCES roles(id)"""))
            await conn.execute(text("INSERT INTO roles VALUES(1,'ADMIN')"))
            await conn.execute(text("INSERT INTO account(id,email,username,password_hash,role_id) VALUES(1,'admin@example.com','admin','unused',1)"))
            await conn.run_sync(KnowledgeDocument.__table__.create)
        async with self.factory() as db:
            db.add(KnowledgeDocument(id=self.source_id, title='Heritage', bucket='test-bucket',
                object_key='curated/history.txt', filename='history.txt', content_type='text/plain',
                size_bytes=len(self.body), etag='"etag"', revision=1, status='uploaded'))
            await db.commit()

    async def pipeline(self, name='Heritage'):
        async with self.factory() as db:
            return await PipelineService(db).create(PipelineCreate(name=name,
                chunking={'max_chars': 80, 'overlap_chars': 10}))

    async def schedule(self, pipeline):
        async with self.factory() as db:
            return await PipelineService(db).trigger(pipeline.id, [self.source_id], '1')

    @staticmethod
    def vectors(texts):
        # Test adapter only: production still calls the unchanged pinned BGE-M3.
        return [[1.0] + [0.0] * 1023 for _ in texts]

    def storage(self):
        client = boto3.client('s3', endpoint_url='https://r2-test.example', region_name='auto',
                              aws_access_key_id='test-only', aws_secret_access_key='test-only')
        self.addCleanup(client.close)
        stubber = self.enterContext(Stubber(client))
        stubber.add_response('get_object', {'Body': StreamingBody(io.BytesIO(self.body), len(self.body)),
                                          'ContentLength': len(self.body)},
                            {'Bucket': 'test-bucket', 'Key': 'curated/history.txt', 'IfMatch': '"etag"'})
        return R2Storage(client=client, bucket='test-bucket'), stubber

    async def test_concurrent_different_pipeline_triggers_share_one_writer_slot(self):
        first, second = await self.pipeline('One'), await self.pipeline('Two')
        async def trigger(pipeline):
            try:
                await self.schedule(pipeline)
                return 202
            except HTTPException as error:
                return error.status_code
        results = await asyncio.gather(trigger(first), trigger(second))
        self.assertEqual(sorted(results), [202, 409])
        async with self.factory() as db:
            active = (await db.scalars(select(ReindexJob).where(ReindexJob.active_slot == 1))).all()
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0].status, 'PENDING')

    async def test_worker_claims_once_and_persists_real_checkpoints(self):
        job = await self.schedule(await self.pipeline())
        storage, stubber = self.storage()
        indexed, prune_queries = [], []
        def respond(request):
            if request.url.path == '/_bulk':
                lines = request.content.decode().splitlines()
                indexed.extend(json.loads(row) for row in lines[1::2])
                return httpx.Response(200, json={'errors': False})
            if request.url.path.endswith('/_delete_by_query'):
                prune_queries.append(json.loads(request.content))
                return httpx.Response(200, json={'deleted': 0})
            return httpx.Response(200, json={'acknowledged': True})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            async with PassageStore(url='http://search-test.example', index='sprint4-test', client=client) as store:
                claims = await asyncio.gather(*[run_next(self.factory, storage=storage, store=store,
                                                        embedder=self.vectors) for _ in range(2)])
        self.assertEqual(sum(claims), 1)
        stubber.assert_no_pending_responses()
        async with self.factory() as db:
            actual = await db.get(ReindexJob, job.id)
            self.assertEqual(actual.status, 'COMPLETED')
            self.assertIsNone(actual.active_slot)
            self.assertEqual(actual.processed_documents, 1)
            self.assertEqual(actual.indexed_passages, len(indexed))
            self.assertGreater(len(indexed), 1)
            self.assertIsNotNone(actual.started_at.tzinfo)
            self.assertIsNotNone(actual.finished_at)
            self.assertEqual((await db.get(KnowledgeDocument, self.source_id)).status, 'indexed')
        self.assertTrue(all(len(row['embedding']) == 1024 for row in indexed))
        self.assertEqual(prune_queries[0]['query']['bool']['filter'],
                         [{'term': {'object_key': 'curated/history.txt'}}, {'term': {'bucket': 'test-bucket'}}])
        self.assertEqual(set(prune_queries[0]['query']['bool']['must_not'][0]['ids']['values']),
                         {row['id'] for row in indexed})

    async def test_search_failure_marks_failed_and_retains_uploaded_source(self):
        job = await self.schedule(await self.pipeline())
        storage, _ = self.storage()
        def respond(request):
            if request.url.path == '/_bulk':
                return httpx.Response(503, text='private-dependency-token')
            return httpx.Response(200, json={'acknowledged': True})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            async with PassageStore(url='http://search-test.example', index='sprint4-test', client=client) as store:
                await run_next(self.factory, storage=storage, store=store, embedder=self.vectors)
        async with self.factory() as db:
            actual = await db.get(ReindexJob, job.id)
            self.assertEqual(actual.status, 'FAILED')
            self.assertIsNone(actual.active_slot)
            self.assertEqual(actual.processed_documents, 0)
            self.assertNotIn('private-dependency-token', actual.error)
            self.assertEqual((await db.get(KnowledgeDocument, self.source_id)).status, 'uploaded')
