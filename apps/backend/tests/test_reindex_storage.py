"""Real S3 adapter validation with protocol responses; no external requests."""
import io
import unittest
from types import SimpleNamespace

import boto3
from botocore.response import StreamingBody
from botocore.stub import Stubber
from fastapi import HTTPException

from apps.backend.core.r2 import R2Storage
from apps.backend.services.reindex_worker import read_document


class ReindexStorageTests(unittest.TestCase):
    def setUp(self):
        client = boto3.client('s3', endpoint_url='https://r2-test.example', region_name='auto',
                              aws_access_key_id='test-only', aws_secret_access_key='test-only')
        self.addCleanup(client.close)
        self.stubber = self.enterContext(Stubber(client))
        self.storage = R2Storage(client=client, bucket='test-bucket')
        self.document = SimpleNamespace(size_bytes=16, object_key='curated/history.txt',
                                        etag='"current-etag"', filename='history.txt')
        self.params = {'Bucket': 'test-bucket', 'Key': 'curated/history.txt', 'IfMatch': '"current-etag"'}

    def test_actual_sdk_uses_bucket_key_and_etag_and_closes_the_stream(self):
        raw = io.BytesIO(b'Heritage history')
        self.stubber.add_response('get_object', {'Body': StreamingBody(raw, 16), 'ContentLength': 16}, self.params)
        self.assertEqual(read_document(self.storage, self.document), 'Heritage history')
        self.assertTrue(raw.closed)
        self.stubber.assert_no_pending_responses()

    def test_stale_etag_is_a_safe_conflict(self):
        self.stubber.add_client_error('get_object', service_error_code='PreconditionFailed',
            service_message='private-signed-source-url', http_status_code=412, expected_params=self.params)
        with self.assertRaises(HTTPException) as result:
            read_document(self.storage, self.document)
        self.assertEqual(result.exception.status_code, 409)
        self.assertNotIn('private-signed-source-url', result.exception.detail)

    def test_changed_size_and_oversized_response_close_the_stream(self):
        for body, length in ((b'short', 5), (b'content', 16 * 1024 * 1024 + 1)):
            with self.subTest(length=length):
                raw = io.BytesIO(body)
                self.stubber.add_response('get_object', {'Body': StreamingBody(raw, len(body)),
                                                        'ContentLength': length}, self.params)
                with self.assertRaises(ValueError):
                    read_document(self.storage, self.document)
                self.assertTrue(raw.closed)

    def test_oversized_registered_document_never_requests_storage(self):
        self.document.size_bytes = 16 * 1024 * 1024 + 1
        with self.assertRaises(ValueError):
            read_document(self.storage, self.document)
        self.stubber.assert_no_pending_responses()
