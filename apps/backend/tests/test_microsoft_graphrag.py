"""Optional GraphRAG contract: isolated snapshots and honest R2 provenance."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from apps.backend.app import app
from pipelines.graph.microsoft_graphrag import build_global_response, export_snapshot


class MicrosoftGraphRagTests(unittest.TestCase):
    def test_export_preserves_passage_identity_and_refuses_overwrite(self):
        rows = [{'id': 42, 'object_key': 'processed/passages/hash.json',
                 'content_hash': 'hash', 'location_note': 'Chùa Thiên Mụ'}]

        class Store:
            bucket = 'knowledge'

            def read_text(self, key, digest):
                return 'Chùa Thiên Mụ nằm ở Huế.'

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'snapshot'
            export_snapshot(rows, Store(), root)
            self.assertEqual((root / 'input/passage-42.txt').read_text(),
                             'Chùa Thiên Mụ nằm ở Huế.')
            manifest = json.loads((root / 'source-manifest.json').read_text())
            source = manifest['documents']['passage-42.txt']
            self.assertEqual(source['passage_id'], 42)
            self.assertEqual(source['object_key'], rows[0]['object_key'])
            self.assertEqual(source['bucket'], 'knowledge')
            self.assertTrue((root / 'settings.yaml').is_file())
            with self.assertRaises(FileExistsError):
                export_snapshot(rows, Store(), root)
            self.assertEqual(json.loads((root / 'source-manifest.json').read_text()), manifest)

    def test_failed_source_read_does_not_publish_partial_snapshot(self):
        class Store:
            bucket = 'knowledge'

            def read_text(self, key, digest):
                raise ValueError('checksum mismatch')

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'snapshot'
            with self.assertRaises(ValueError):
                export_snapshot([{'id': 5, 'object_key': 'bad', 'content_hash': 'bad'}], Store(), root)
            self.assertFalse(root.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_global_sources_follow_community_ids_not_report_row_ids(self):
        manifest = {'snapshot_id': 'sample', 'documents': {
            'passage-42.txt': {'passage_id': 42, 'object_key': 'key42', 'content_hash': 'h42',
                               'bucket': 'knowledge', 'doc': 'Thiên Mụ'},
            'passage-91.txt': {'passage_id': 91, 'object_key': 'key91', 'content_hash': 'h91',
                               'bucket': 'knowledge', 'doc': 'Khác'},
        }}
        reports = [{'id': 'uuid-report', 'human_readable_id': 999, 'community': 7,
                    'level': 0, 'title': 'Di sản Huế'},
                   {'id': 'other', 'human_readable_id': 7, 'community': 12,
                    'level': 0, 'title': 'Không được chọn'}]
        communities = [{'community': 7, 'level': 0, 'text_unit_ids': ['tu-b', 'tu-a']},
                       {'community': 12, 'level': 0, 'text_unit_ids': ['tu-c']}]
        units = [{'id': 'tu-a', 'document_id': 'doc-a'},
                 {'id': 'tu-b', 'document_id': 'doc-a'},
                 {'id': 'tu-c', 'document_id': 'doc-c'}]
        documents = [{'id': 'doc-a', 'title': 'passage-42.txt'},
                     {'id': 'doc-c', 'title': 'passage-91.txt'}]
        result = build_global_response('Di sản Huế [Data: Reports (7)]', [{'id': '7'}],
                                       reports, communities, units, documents, manifest)
        self.assertEqual(result['answer'], 'Di sản Huế [Data: Reports (7)]')
        self.assertEqual([s['passage_id'] for s in result['sources']], [42])
        self.assertEqual(result['sources'][0]['report_ids'], ['7'])
        self.assertEqual(result['context_reports'][0]['report_id'], '7')
        self.assertFalse(result['grounding_verified'])
        self.assertEqual(result['source_scope'], 'community_context')
        # Never manufacture sources when upstream returns no context.
        empty = build_global_response('No data', [], reports, communities, units, documents, manifest)
        self.assertEqual(empty['sources'], [])
        # A broken lineage must fail rather than silently omit a reference.
        with self.assertRaises(ValueError):
            build_global_response('answer', [{'id': '7'}], reports, communities,
                                  units, [], manifest)
        with self.assertRaises(ValueError):
            build_global_response('answer', [{'id': '404'}], reports, communities,
                                  units, documents, manifest)

    def test_optional_endpoint_is_disabled_by_default_and_validates_request(self):
        with patch.dict(os.environ, {'GRAPHRAG_ENABLED': 'false'}):
            client = TestClient(app)
            response = client.post('/api/graphrag/query', json={'message': 'Tổng quan di sản?'})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(client.post('/api/graphrag/query', json={'message': '  '}).status_code, 422)
            self.assertEqual(client.post('/api/graphrag/query', json={
                'message': 'test', 'community_level': -1,
            }).status_code, 422)

    def test_endpoint_returns_global_provenance_and_sanitizes_worker_errors(self):
        result = {'answer': 'Tổng quan', 'snapshot_id': 'sample', 'context_reports': [],
                  'sources': [], 'source_scope': 'community_context', 'grounding_verified': False}
        with patch('apps.backend.api.graphrag.run_global_query', new_callable=AsyncMock) as query:
            query.return_value = result
            client = TestClient(app)
            response = client.post('/api/graphrag/query', json={'message': 'Tổng quan?'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), result)
            query.side_effect = RuntimeError('token=private-worker-error')
            response = client.post('/api/graphrag/query', json={'message': 'Tổng quan?'})
            self.assertEqual(response.status_code, 503)
            self.assertNotIn('private-worker-error', response.text)


if __name__ == '__main__':
    unittest.main()
