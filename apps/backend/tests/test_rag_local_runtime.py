"""Real PostgreSQL/BGE-M3/OpenSearch; the only fixture is the S3 protocol response.

No cloud connection or object is used. The production worker, chunker,
embedding provider, HTTP search adapter and admin endpoints run unchanged.
"""
import io
import os
import unittest
from unittest.mock import patch

import boto3
from botocore.response import StreamingBody
from botocore.stub import Stubber

from apps.backend.core.r2 import R2Storage
from apps.backend.tests import test_rag_live as fixtures


@unittest.skipUnless(os.environ.get('RAG_LOCAL_RUNTIME_TEST') == '1', 'explicit local RAG runtime required')
class RagLocalRuntimeTests(fixtures.RagLiveTests):
    # Use this class's local-runtime gate, rather than inheriting the disabled
    # cloud gate from the shared end-to-end test implementation.
    __unittest_skip__ = False

    async def asyncSetUp(self):
        self.enterContext(patch.dict(os.environ, {
            'R2_BUCKET': 'test-bucket', 'R2_KNOWLEDGE_PREFIX': 'curated/',
            'RAG_TEST_R2_OBJECT_KEY': 'curated/runtime-smoke.txt',
        }))
        await super().asyncSetUp()

    def source_storage(self):
        client = boto3.client('s3', endpoint_url='http://127.0.0.1:1', region_name='auto',
                              aws_access_key_id='test-only', aws_secret_access_key='test-only')
        stubber = self.enterContext(Stubber(client))
        body = ('Tài liệu kiểm thử pipeline RAG. Các đoạn văn được tạo vector BGE-M3 '
                'và lưu vào OpenSearch. Kết quả công việc được lưu trong PostgreSQL.\n').encode()
        params = {'Bucket': 'test-bucket', 'Key': 'curated/runtime-smoke.txt'}
        stubber.add_response('head_object', {'ContentLength': len(body), 'ETag': '"runtime-etag"',
                                            'ContentType': 'text/plain'}, params)
        stubber.add_response('get_object', {'ContentLength': len(body),
            'Body': StreamingBody(io.BytesIO(body), len(body))}, {**params, 'IfMatch': '"runtime-etag"'})
        self.addCleanup(stubber.assert_no_pending_responses)
        return R2Storage(client=client, bucket='test-bucket'), 'curated/runtime-smoke.txt'
