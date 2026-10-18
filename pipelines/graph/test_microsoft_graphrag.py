"""Run with .venv-graphrag: pinned SDK + real config/Parquet, no LLM calls."""
import os
import tempfile
import unittest
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from unittest.mock import AsyncMock, patch

from pipelines.graph.microsoft_graphrag import export_snapshot, index_snapshot, query_snapshot

try:
    HAS_SDK = version('graphrag') == '3.3.0'
except PackageNotFoundError:
    HAS_SDK = False


@unittest.skipUnless(HAS_SDK, 'run in the isolated GraphRAG 3.3.0 environment')
class GraphRagSdkTests(unittest.IsolatedAsyncioTestCase):
    async def test_index_publishes_only_successful_resolvable_snapshots(self):
        import pandas as pd
        from graphrag.index.typing.pipeline_run_result import PipelineRunResult

        class Store:
            bucket = 'test'

            def read_text(self, key, digest):
                return 'Chùa Thiên Mụ ở Huế.'

        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'snapshot'
            export_snapshot([{'id': 42, 'object_key': 'key42', 'content_hash': 'h42'}], Store(), root)
            try:
                failed = PipelineRunResult(workflow='extract_graph', result=None, state={},
                                           error=RuntimeError('extraction failed'))
                with patch('graphrag.api.build_index', new=AsyncMock(return_value=[failed])):
                    with self.assertRaisesRegex(RuntimeError, 'indexing failed'):
                        await index_snapshot(root)
                self.assertFalse((root / 'index-ready.json').exists())

                async def successful_index(config):
                    data = {
                        'entities': [{'id': 'entity', 'title': 'Thiên Mụ',
                                      'description': 'Ngôi chùa ở Huế.', 'text_unit_ids': ['tu']}],
                        'relationships': [{'id': 'relation', 'source': 'Thiên Mụ', 'target': 'Huế',
                                           'description': 'Ngôi chùa nằm ở Huế.', 'text_unit_ids': ['tu']}],
                        'communities': [{'community': 7, 'level': 0, 'text_unit_ids': ['tu'],
                                         'entity_ids': ['entity'], 'relationship_ids': ['relation']}],
                        'community_reports': [{'id': 'uuid', 'community': 7, 'level': 0, 'title': 'Huế'}],
                        'text_units': [{'id': 'tu', 'document_id': 'doc'}],
                        'documents': [{'id': 'doc', 'title': 'passage-42.txt'}],
                    }
                    (root / 'output').mkdir(exist_ok=True)
                    for name, rows in data.items():
                        pd.DataFrame(rows).to_parquet(root / 'output' / f'{name}.parquet')
                    return [PipelineRunResult(workflow='create_community_reports', result=None,
                                              state={}, error=None)]

                with patch('graphrag.api.build_index', new=successful_index):
                    await index_snapshot(root)
                self.assertTrue((root / 'index-ready.json').is_file())
                with patch('graphrag.api.global_search', new=AsyncMock(return_value=(
                    'Thiên Mụ ở Huế [Data: Reports (7)]', {'reports': pd.DataFrame([{'id': '7'}])},
                ))):
                    response = await query_snapshot(root, 'Tổng quan?', 0)
                self.assertEqual(response['sources'][0]['passage_id'], 42)
                self.assertEqual(response['sources'][0]['report_ids'], ['7'])
                self.assertFalse(response['grounding_verified'])
                self.assertEqual({item['kind'] for item in response['graph_context']},
                                 {'entity', 'relationship'})
                self.assertTrue(all(item['source_passage_ids'] == [42]
                                    for item in response['graph_context']))
                (root / 'output/relationships.parquet').write_bytes(b'tampered relationship')
                with self.assertRaisesRegex(ValueError, 'snapshot changed'):
                    await query_snapshot(root, 'Tổng quan?', 0)
            finally:
                os.chdir(previous)


if __name__ == '__main__':
    unittest.main()
