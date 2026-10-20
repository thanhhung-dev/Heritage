"""Local admin API contract; no calls to the real R2 bucket or PostgreSQL."""
import asyncio
import io
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
from botocore.exceptions import ClientError
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


class MemoryS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body=b'', ContentType='application/octet-stream', **kwargs):
        self.objects[Key] = {'body': Body, 'type': ContentType, 'etag': f'"{len(Body)}"'}

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({'Error': {'Code': '404'}}, 'HeadObject')
        obj = self.objects[Key]
        return {'ContentLength': len(obj['body']), 'ContentType': obj['type'],
                'ETag': obj['etag'], 'LastModified': datetime.now(timezone.utc)}

    def get_object(self, Bucket, Key, **kwargs):
        return {'Body': io.BytesIO(self.objects[Key]['body'][:4096])}

    def copy_object(self, Bucket, Key, CopySource, CopySourceIfMatch):
        source = self.objects[CopySource['Key']]
        assert source['etag'] == CopySourceIfMatch
        self.objects[Key] = dict(source)
        return {'CopyObjectResult': {'ETag': source['etag']}}

    def delete_object(self, Bucket, Key):
        self.objects.pop(Key, None)

    def list_objects_v2(self, Bucket, Prefix, Delimiter=None, MaxKeys=1000, ContinuationToken=None):
        keys = sorted(k for k in self.objects if k.startswith(Prefix))
        folders, files = set(), []
        for key in keys:
            suffix = key[len(Prefix):]
            if Delimiter and '/' in suffix:
                folders.add(Prefix + suffix.split('/')[0] + '/')
            else:
                files.append({'Key': key, 'Size': len(self.objects[key]['body']),
                              'LastModified': datetime.now(timezone.utc)})
        entries = [('folder', x) for x in sorted(folders)] + [('file', x) for x in files]
        start = int(ContinuationToken or 0)
        page = entries[start:start + MaxKeys]
        result = {'CommonPrefixes': [{'Prefix': x} for kind, x in page if kind == 'folder'],
                  'Contents': [x for kind, x in page if kind == 'file'],
                  'IsTruncated': start + MaxKeys < len(entries)}
        if result['IsTruncated']:
            result['NextContinuationToken'] = str(start + MaxKeys)
        return result

    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):
        return f'https://test.invalid/{Params["Key"]}?signature=test'


class AdminKnowledgeTests(unittest.TestCase):
    def setUp(self):
        # Import inside the test so RED runs and reports the missing feature.
        from apps.backend.api import admin_knowledge as api
        from apps.backend.models.knowledge import KnowledgeDocument, KnowledgeUpload
        from apps.backend.core.r2 import R2Storage
        self.api = api
        self.env = self.enterContext(patch.dict(os.environ, {
            'APP_ENVIRONMENT': 'local', 'R2_KNOWLEDGE_PREFIX': 'knowledge/',
            'R2_UPLOAD_MAX_BYTES': '100', 'CORS_ORIGINS': '',
        }))
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.engine = create_async_engine(f'sqlite+aiosqlite:///{Path(self.temp) / "test.db"}')
        async def create():
            async with self.engine.begin() as conn:
                await conn.run_sync(lambda c: KnowledgeDocument.metadata.create_all(
                    c, tables=[KnowledgeDocument.__table__, KnowledgeUpload.__table__]))
        asyncio.run(create())
        factory = async_sessionmaker(self.engine, expire_on_commit=False)
        async def database():
            async with factory() as session:
                yield session
        self.s3 = MemoryS3()
        self.storage = R2Storage(client=self.s3, bucket='test-bucket')
        app = FastAPI()
        app.include_router(api.router, prefix='/api')
        app.dependency_overrides[api.get_storage] = lambda: self.storage
        app.dependency_overrides[api.get_db] = database
        self.client = self.enterContext(TestClient(app))
        self.addCleanup(lambda: asyncio.run(self.engine.dispose()))

    def upload(self, *, document_id=None, text=b'Thien Mu nam 1601.', parent='knowledge/hue/'):
        payload = {'parent_prefix': parent, 'filename': 'lich-su.txt',
                   'content_type': 'text/plain', 'size_bytes': len(text)}
        if document_id:
            payload['document_id'] = document_id
        response = self.client.post('/api/admin/uploads', json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()
        from urllib.parse import unquote, urlsplit
        key = unquote(urlsplit(data['upload_url']).path.lstrip('/'))
        self.s3.put_object(Bucket='test-bucket', Key=key, Body=text, ContentType='text/plain')
        return data['upload_id']

    def test_folder_crud_and_pagination_do_not_escape_root(self):
        url = '/api/admin/storage/folders'
        r = self.client.post(url, json={'parent_prefix': 'knowledge/hue/', 'name': 'thien-mu'})
        self.assertEqual(r.status_code, 201, r.text)
        self.s3.put_object(Bucket='test-bucket', Key='knowledge/hue/a.txt', Body=b'a')
        self.s3.put_object(Bucket='test-bucket', Key='private/secret.txt', Body=b'secret')
        first = self.client.get('/api/admin/storage/entries', params={'prefix': 'knowledge/hue/', 'limit': 1}).json()
        self.assertEqual(first['entries'][0]['kind'], 'folder')
        self.assertTrue(first['next_cursor'])
        second = self.client.get('/api/admin/storage/entries', params={
            'prefix': 'knowledge/hue/', 'limit': 1, 'cursor': first['next_cursor']}).json()
        self.assertEqual(second['entries'][0]['key'], 'knowledge/hue/a.txt')
        self.assertEqual(self.client.patch(url, json={
            'prefix': 'knowledge/hue/thien-mu/', 'name': 'linh-mu'}).status_code, 200)
        self.assertEqual(self.client.delete(url, params={'prefix': 'knowledge/hue/linh-mu/'}).status_code, 204)
        for prefix in ['private/', 'knowledge-evil/', 'knowledge/../private/', 'knowledge/%2e%2e/', '/knowledge/']:
            self.assertEqual(self.client.get('/api/admin/storage/entries', params={'prefix': prefix}).status_code, 422)
        self.assertEqual(self.client.delete(url, params={'prefix': 'knowledge/hue/'}).status_code, 409)
        self.assertEqual(self.client.delete(url, params={'prefix': 'knowledge/'}).status_code, 422)

    def test_upload_complete_metadata_replace_and_delete(self):
        upload_id = self.upload()
        complete = f'/api/admin/uploads/{upload_id}/complete'
        response = self.client.post(complete)
        self.assertEqual(response.status_code, 200, response.text)
        doc = response.json()
        doc_id, old_key = doc['id'], doc['object_key']
        self.assertEqual(self.client.post(complete).json()['id'], doc_id)
        # Reusing the signed staging URL cannot alter the completed document.
        staging = next(k for k in self.s3.objects if k.startswith('_admin_uploads/'))
        self.s3.objects[staging]['body'] = b'changed'
        self.assertEqual(self.s3.objects[old_key]['body'], b'Thien Mu nam 1601.')
        path = f'/api/admin/documents/{doc_id}'
        changed = self.client.patch(path, json={'title': 'Thiên Mụ', 'region': 'hue',
                                               'source_url': 'https://example.org/thien-mu'})
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()['title'], 'Thiên Mụ')
        self.assertEqual(self.client.get('/api/admin/documents', params={'status': 'uploaded'}).json()['items'][0]['id'], doc_id)
        self.assertIn('url', self.client.get(path + '/download-url').json())
        self.assertEqual(self.client.get(path + '/chunks').json()['items'], [])
        replacement = self.upload(document_id=doc_id, text=b'Ban moi 1710.')
        new_doc = self.client.post(f'/api/admin/uploads/{replacement}/complete').json()
        self.assertNotEqual(new_doc['object_key'], old_key)
        self.assertIn(old_key, self.s3.objects)
        self.assertEqual(new_doc['title'], 'Thiên Mụ')
        self.assertEqual(self.client.delete(path).status_code, 204)
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.post(complete).status_code, 409)

    def test_bad_uploads_and_metadata_are_rejected(self):
        for filename, size in [('bad.exe', 5), ('../a.txt', 5), ('a.txt', 101), ('a.txt', 0)]:
            r = self.client.post('/api/admin/uploads', json={'parent_prefix': 'knowledge/',
                'filename': filename, 'content_type': 'text/plain', 'size_bytes': size})
            self.assertEqual(r.status_code, 422, r.text)
        uid = self.upload(text=b'\x00not-text')
        self.assertEqual(self.client.post(f'/api/admin/uploads/{uid}/complete').status_code, 422)
        uid = self.upload()
        doc = self.client.post(f'/api/admin/uploads/{uid}/complete').json()
        self.assertEqual(self.client.patch(f'/api/admin/documents/{doc["id"]}', json={
            'source_url': 'https://example.org/?token=secret'}).status_code, 422)

    def test_local_only_and_browser_origin_guard(self):
        with patch.dict(os.environ, {'APP_ENVIRONMENT': 'production'}):
            self.assertEqual(self.client.get('/api/admin/storage/entries').status_code, 403)
        self.assertEqual(self.client.post('/api/admin/storage/folders',
            headers={'Origin': 'https://evil.example'}, json={
                'parent_prefix': 'knowledge/', 'name': 'bad'}).status_code, 403)

    def test_stale_replacements_do_not_overwrite_newer_document(self):
        uid = self.upload()
        doc = self.client.post(f'/api/admin/uploads/{uid}/complete').json()
        a = self.upload(document_id=doc['id'], text=b'Version A')
        b = self.upload(document_id=doc['id'], text=b'Version B')
        self.assertEqual(self.client.post(f'/api/admin/uploads/{b}/complete').status_code, 200)
        self.assertEqual(self.client.post(f'/api/admin/uploads/{a}/complete').status_code, 409)


if __name__ == '__main__':
    unittest.main()
