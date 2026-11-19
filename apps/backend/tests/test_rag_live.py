"""Explicit full-stack smoke test: real PostgreSQL, R2 read, BGE-M3 and OpenSearch.

Requires RAG_LIVE_TEST=1, SPRINT4_POSTGRES_TEST_URL, OPENSEARCH_TEST_URL,
RAG_TEST_R2_OBJECT_KEY, and ordinary R2 credentials/bucket/prefix. Never writes
R2, never falls back to the application database/index, and never downloads
model weights automatically. Uses its own temporary PostgreSQL schema/index.
"""
import asyncio
import os
import secrets
import unittest
from pathlib import PurePosixPath
from uuid import uuid4
from unittest.mock import patch

from anyio import CancelScope
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.backend.api.admin import auth, rag
from apps.backend.core.r2 import R2Storage, knowledge_prefix, safe_name
from apps.backend.core.search import PassageStore
from apps.backend.core.security import get_auth_db, hash_password
from apps.backend.models.knowledge import KnowledgeDocument
from apps.backend.models.revoked_token import RevokedToken
from apps.backend.services.reindex_worker import run_next
from apps.backend.tests import test_sprint4_postgres as fixtures


@unittest.skipUnless(os.environ.get('RAG_LIVE_TEST') == '1', 'explicit full-stack RAG test resources required')
class RagLiveTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(fixtures.Sprint4PostgresTests.setUpClass.__func__)
    drop_schema = fixtures.Sprint4PostgresTests.drop_schema

    async def asyncSetUp(self):
        for key in ('SPRINT4_POSTGRES_TEST_URL', 'OPENSEARCH_TEST_URL', 'RAG_TEST_R2_OBJECT_KEY', 'R2_BUCKET'):
            if not os.environ.get(key):
                self.fail(f'{key} must be explicitly configured for this live test')
        await fixtures.Sprint4PostgresTests.asyncSetUp(self)
        self.enterContext(patch.dict(os.environ, {
            'JWT_SECRET_KEY': secrets.token_urlsafe(48), 'JWT_ISSUER': '', 'JWT_AUDIENCE': '',
            'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
        }))
        self.storage = R2Storage()
        self.addCleanup(self.storage.client.close)
        self.source_key = os.environ['RAG_TEST_R2_OBJECT_KEY']
        parent, _, filename = self.source_key.rpartition('/')
        knowledge_prefix(parent + '/')
        safe_name(filename)
        if PurePosixPath(filename).suffix.lower() not in {'.txt', '.md', '.html', '.pdf'}:
            self.fail('Live source must be a supported registered-document format')
        head = await asyncio.to_thread(self.storage.call, 'head_object', Key=self.source_key)
        if not 0 < head['ContentLength'] <= 16 * 1024 * 1024:
            self.fail('Live source must be nonempty and at most 16 MiB')
        self.password = secrets.token_urlsafe(32)
        password_hash = await asyncio.to_thread(hash_password, self.password)
        async with self.engine.begin() as conn:
            await conn.execute(text('CREATE TABLE roles(id INTEGER PRIMARY KEY, name TEXT NOT NULL)'))
            await conn.execute(text('ALTER TABLE account ADD COLUMN email TEXT, ADD COLUMN username TEXT, '
                'ADD COLUMN password_hash TEXT, ADD COLUMN locked_until TIMESTAMPTZ, ADD COLUMN role_id INTEGER'))
            await conn.execute(text("INSERT INTO roles VALUES(1,'ADMIN')"))
            await conn.execute(text("INSERT INTO account(id,email,username,password_hash,role_id) "
                "VALUES(1,'admin@example.com','admin',:password_hash,1)"), {'password_hash': password_hash})
            await conn.run_sync(KnowledgeDocument.__table__.create)
            await conn.run_sync(RevokedToken.__table__.create)
        self.document_id = str(uuid4())
        async with self.factory() as db:
            db.add(KnowledgeDocument(id=self.document_id, title='RAG live test source', bucket=self.storage.bucket,
                object_key=self.source_key, filename=filename, content_type=head.get('ContentType', 'text/plain'),
                size_bytes=head['ContentLength'], etag=head['ETag'], revision=1, status='uploaded'))
            await db.commit()
        self.store = await PassageStore(url=os.environ['OPENSEARCH_TEST_URL'],
                                        index='sprint4-live-test-' + uuid4().hex).__aenter__()
        self.addAsyncCleanup(self.store.__aexit__, None, None, None)
        self.addAsyncCleanup(self.remove_test_index)

    async def remove_test_index(self):
        for path in (f'/{self.store.index}', f'/_search/pipeline/{self.store.index}-hybrid'):
            result = await self.store.client.delete(self.store.url + path)
            if result.status_code not in {200, 404}:
                self.fail('Could not remove the isolated live-test search resource')

    async def test_admin_trigger_worker_and_actual_indexed_vectors(self):
        async def database():
            session = self.factory()
            try:
                yield session
            finally:
                with CancelScope(shield=True):
                    await session.close()
        app = FastAPI()
        app.include_router(auth.router)
        app.include_router(rag.router)
        app.dependency_overrides[get_auth_db] = database
        with TestClient(app) as client:
            login = client.post('/api/admin/login', json={'email': 'admin@example.com', 'password': self.password})
            self.assertEqual(login.status_code, 200)
            client.headers['Authorization'] = 'Bearer ' + login.json()['access_token']
            result = client.post('/api/admin/rag/pipelines', json={'name': 'Full-stack smoke'})
            self.assertEqual(result.status_code, 201)
            pipeline_id = result.json()['id']
            result = client.post(f'/api/admin/rag/pipelines/{pipeline_id}/reindex',
                                 json={'document_ids': [self.document_id]})
            self.assertEqual(result.status_code, 202)
            job_id = result.json()['id']
            self.assertEqual(result.json()['status'], 'PENDING')
            await run_next(self.factory, storage=self.storage, store=self.store)
            actual = client.get(f'/api/admin/rag/jobs/{job_id}').json()
            self.assertEqual(actual['status'], 'COMPLETED', actual.get('error'))
            self.assertEqual(actual['processed_documents'], 1)
            self.assertGreater(actual['indexed_passages'], 0)
            rows = await self.store.export_passages(actual['indexed_passages'] + 1)
            self.assertEqual(len(rows), actual['indexed_passages'])
            vectors = await self.store._request('POST', f'/{self.store.index}/_search',
                                                json={'size': 1, 'query': {'match_all': {}}})
            self.assertEqual(len(vectors['hits']['hits'][0]['_source']['embedding']), 1024)
