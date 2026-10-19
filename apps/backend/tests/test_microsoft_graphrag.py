"""Optional GraphRAG contract: isolated snapshots and honest R2 provenance."""
import asyncio
import json
import os
import sys
import tempfile
import unittest
import venv
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from apps.backend.app import app
from apps.backend.services.graphrag import run_global_query
from pipelines.graph.microsoft_graphrag import build_global_response, export_snapshot, query_snapshot


class MicrosoftGraphRagTests(unittest.TestCase):
    def test_export_uses_opensearch_text_and_string_ids_without_r2(self):
        rows = [{'id': 'PSG-example', 'text': 'Chùa Thiên Mụ nằm ở Huế.',
                 'object_key': 'documents/temple.pdf', 'bucket': 'knowledge',
                 'content_hash': 'hash', 'location_note': 'Chùa Thiên Mụ'}]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'snapshot'
            export_snapshot(rows, root)
            self.assertEqual((root / 'input/passage-PSG-example.txt').read_text(), rows[0]['text'])
            manifest = json.loads((root / 'source-manifest.json').read_text())
            self.assertEqual(manifest['documents']['passage-PSG-example.txt']['passage_id'], 'PSG-example')

    def test_export_preserves_passage_identity_and_refuses_overwrite(self):
        rows = [{'id': 42, 'object_key': 'processed/passages/hash.json',
                 'content_hash': 'hash', 'location_note': 'Chùa Thiên Mụ',
                 'text': 'Chùa Thiên Mụ nằm ở Huế.', 'bucket': 'knowledge'}]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'snapshot'
            export_snapshot(rows, root)
            self.assertEqual((root / 'input/passage-42.txt').read_text(),
                             'Chùa Thiên Mụ nằm ở Huế.')
            manifest = json.loads((root / 'source-manifest.json').read_text())
            source = manifest['documents']['passage-42.txt']
            self.assertEqual(source['passage_id'], 42)
            self.assertEqual(source['object_key'], rows[0]['object_key'])
            self.assertEqual(source['bucket'], 'knowledge')
            self.assertTrue((root / 'settings.yaml').is_file())
            with self.assertRaises(FileExistsError):
                export_snapshot(rows, root)
            self.assertEqual(json.loads((root / 'source-manifest.json').read_text()), manifest)

    def test_incomplete_source_does_not_publish_partial_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'snapshot'
            with self.assertRaises(KeyError):
                export_snapshot([
                    {'id': 4, 'text': 'Valid chunk.', 'content_hash': 'hash'},
                    {'id': 5, 'object_key': 'bad', 'content_hash': 'bad'},
                ], root)
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

    def test_graph_context_has_item_level_lineage_not_just_community_sources(self):
        manifest = {'snapshot_id': 'sample', 'documents': {
            f'passage-{i}.txt': {'passage_id': i, 'object_key': f'key{i}', 'content_hash': f'h{i}',
                               'bucket': 'knowledge', 'doc': str(i)} for i in (42, 91)
        }}
        reports = [{'community': 7, 'level': 0, 'title': 'Huế'}]
        communities = [{'community': 7, 'level': 0, 'text_unit_ids': ['tu-a'],
                        'entity_ids': ['temple', 'mixed'], 'relationship_ids': ['gate-link']}]
        units = [{'id': 'tu-a', 'document_id': 'doc-a'}, {'id': 'tu-b', 'document_id': 'doc-b'}]
        documents = [{'id': 'doc-a', 'title': 'passage-42.txt'},
                     {'id': 'doc-b', 'title': 'passage-91.txt'}]
        entities = [
            {'id': 'temple', 'title': 'Chùa Thiên Mụ', 'description': 'Ngôi chùa ở Huế.',
             'text_unit_ids': ['tu-a']},
            {'id': 'mixed', 'title': 'MIXED', 'description': 'Needs an unselected source.',
             'text_unit_ids': ['tu-a', 'tu-b']},
            {'id': 'unselected', 'title': 'OTHER', 'description': 'Not a community member.',
             'text_unit_ids': ['tu-a']},
        ]
        relationships = [{'id': 'gate-link', 'source': 'Cổng Tam Quan', 'target': 'Chùa Thiên Mụ',
                          'description': 'UNVERIFIED_CLAIM: located in China.',
                          'text_unit_ids': ['tu-a', 'tu-a']}]
        result = build_global_response('UNTRUSTED ANSWER', [{'id': '7'}], reports, communities,
                                       units, documents, manifest, entities=entities,
                                       relationships=relationships)
        self.assertEqual({item['id'] for item in result['graph_context']}, {'temple', 'gate-link'})
        for item in result['graph_context']:
            self.assertEqual(item['source_passage_ids'], [42])
        self.assertNotIn('UNTRUSTED ANSWER', json.dumps(result['graph_context']))
        self.assertNotIn('UNVERIFIED_CLAIM', json.dumps(result['graph_context']))
        self.assertTrue(all('description' not in item for item in result['graph_context']))
        self.assertEqual(build_global_response('', [], reports, communities, units, documents,
                                               manifest, entities=entities,
                                               relationships=relationships)['graph_context'], [])

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


class GraphRagProcessTests(unittest.IsolatedAsyncioTestCase):
    async def test_worker_preserves_the_selected_virtualenv(self):
        create_process = asyncio.create_subprocess_exec

        async def launch_probe(python, *args, **kwargs):
            # Probe the actual child environment instead of invoking an LLM.
            code = "import sys,json; print(json.dumps({'answer':sys.prefix,'snapshot_id':'test','sources':[],'context_reports':[]}))"
            return await create_process(python, '-c', code, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            environment = root / 'venv'
            venv.EnvBuilder(with_pip=False, symlinks=True).create(environment)
            (root / 'index-ready.json').write_text('{}')
            with (
                patch.dict(os.environ, {
                    'GRAPHRAG_ENABLED': 'true', 'GRAPHRAG_ROOT': str(root),
                    'GRAPHRAG_PYTHON': str(environment / 'bin/python'),
                }),
                patch('apps.backend.services.graphrag.asyncio.create_subprocess_exec', new=launch_probe),
            ):
                result = await run_global_query('probe')
            self.assertEqual(Path(result['answer']), environment)

    async def test_modified_snapshot_is_rejected_before_loading_model_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'output').mkdir()
            (root / 'source-manifest.json').write_text('{}')
            (root / 'settings.yaml').write_text('not a valid config mapping')
            for name in ('entities', 'relationships', 'communities', 'community_reports', 'text_units', 'documents'):
                (root / 'output' / f'{name}.parquet').write_bytes(b'changed')
            (root / 'index-ready.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'snapshot changed'):
                await query_snapshot(root, 'Tổng quan?', 0)

    async def test_worker_protocol_failures_and_timeout_leave_service_usable(self):
        # Exercise a real subprocess boundary, without loading a second AI model.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'index-ready.json').write_text('{}')
            worker = root / 'worker'
            worker.write_text(f'#!{sys.executable}\n' + '''
import json, sys, time
message = json.load(sys.stdin)['message']
if message == 'timeout':
    time.sleep(5)
if message == 'fail':
    print('token=private-subprocess-secret', file=sys.stderr)
    sys.exit(1)
if message == 'invalid':
    print('not json')
else:
    print(json.dumps({'answer': message, 'snapshot_id': 'test', 'context_reports': [],
                      'sources': [], 'source_scope': 'community_context', 'grounding_verified': False}))
''')
            worker.chmod(0o700)
            with patch.dict(os.environ, {
                'GRAPHRAG_ENABLED': 'true', 'GRAPHRAG_ROOT': str(root),
                'GRAPHRAG_PYTHON': str(worker), 'GRAPHRAG_QUERY_TIMEOUT': '2',
            }):
                self.assertEqual((await run_global_query('question'))['answer'], 'question')
                with self.assertRaises(RuntimeError) as error:
                    await run_global_query('fail')
                self.assertNotIn('private-subprocess-secret', str(error.exception))
                with self.assertRaises(ValueError):
                    await run_global_query('invalid')
                with patch.dict(os.environ, {'GRAPHRAG_QUERY_TIMEOUT': '0.05'}), self.assertRaises(TimeoutError):
                    await run_global_query('timeout')
                # Timeout must not leave a stale busy lock or an unusable worker slot.
                self.assertEqual((await run_global_query('after timeout'))['answer'], 'after timeout')


if __name__ == '__main__':
    unittest.main()
