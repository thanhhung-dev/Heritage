"""Optional GraphRAG must resolve sources against current OpenSearch evidence."""
import os
import unittest
from unittest.mock import AsyncMock, patch

from apps.backend.api import chat as chat_api
from apps.backend.services.passages import PassageRepository
from apps.backend.tests.test_opensearch import vectors


class ChatGraphRagTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.row = {'id': '42', 'text': 'Chùa Thiên Mụ được dựng năm 1601.',
                    'object_key': 'raw/temple.pdf', 'content_hash': 'h42', 'bucket': 'knowledge'}
        self.source = {k: self.row[k] for k in ('object_key', 'content_hash', 'bucket')}
        self.source['passage_id'] = 42  # Existing snapshots use integer IDs.
        self.graph = {'sources': [self.source], 'answer': 'UNTRUSTED 9999',
                      'graph_context': [{'kind': 'entity', 'title': 'TEMPLE_CONTEXT',
                                         'source_passage_ids': [42]}]}
        self.store = AsyncMock()
        self.store.search.return_value = []
        self.store.get_passages.return_value = [self.row]
        self.repo = PassageRepository(self.store, embedder=vectors)
        self.enterContext(patch.dict(os.environ, {'GRAPHRAG_ENABLED': 'true'}))
        self.query = self.enterContext(patch('apps.backend.services.passages.run_global_query',
                                             new_callable=AsyncMock, return_value=self.graph))

    async def test_original_chunk_not_generated_graph_answer_reaches_llm(self):
        with patch.object(chat_api, 'generate_response', side_effect=lambda question, context: context):
            response = await chat_api.chat(chat_api.ChatRequest(message='Thiên Mụ liên quan gì?'),
                                           repository=self.repo)
        self.assertIn('1601', response.answer)
        self.assertIn('TEMPLE_CONTEXT', response.answer)
        self.assertNotIn('9999', response.answer)
        self.assertEqual(response.sources[0]['passage_id'], '42')
        self.assertEqual(response.sources[0]['retrieval_methods'], ['microsoft_graphrag'])

    async def test_stale_mapping_or_incomplete_lineage_never_reaches_prompt(self):
        for change in ({'content_hash': 'stale'}, {'object_key': 'replaced'}, {'bucket': 'other'}):
            with self.subTest(change=change):
                self.query.return_value = {**self.graph, 'sources': [{**self.source, **change}]}
                result = await self.repo.search_evidence('Thiên Mụ liên quan gì?')
                self.assertEqual(result.evidence, [])
                self.assertEqual(result.graph_context, [])
        self.query.return_value = self.graph
        self.graph['graph_context'][0]['source_passage_ids'] = [42, 91]
        result = await self.repo.search_evidence('Thiên Mụ liên quan gì?')
        self.assertEqual(len(result.evidence), 1)
        self.assertEqual(result.graph_context, [])

    async def test_graph_failure_preserves_hybrid_evidence(self):
        self.store.search.return_value = [self.row]
        self.query.side_effect = TimeoutError()
        result = await self.repo.search_evidence('Thiên Mụ liên quan gì?')
        self.assertEqual([e.text for e in result.evidence], [self.row['text']])
        self.assertEqual(result.graph_context, [])

    async def test_disabled_graph_does_not_run(self):
        self.query.side_effect = AssertionError('GraphRAG disabled')
        with patch.dict(os.environ, {'GRAPHRAG_ENABLED': 'false'}):
            self.assertEqual((await self.repo.search_evidence('Thiên Mụ')).evidence, [])
