"""OpenSearch passage contract; integration tests use a disposable local index."""
import json
import os
import unittest
import uuid
from unittest.mock import patch

import httpx

from apps.backend.core.search import PassageStore, SearchError
from apps.backend.core.embedding import EMBEDDING_ID
from apps.backend.db.import_passages import import_passages
from apps.backend.services.passages import PassageRepository


def vectors(texts):
    return [[1.0, 0.0] + [0.0] * 1022 if 'thiên mụ' in t.lower()
            or 'thien mu' in t.lower() else [0.0, 1.0] + [0.0] * 1022 for t in texts]


class SearchTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_partial_bulk_failure_is_reported_not_a_successful_import(self):
        def respond(request):
            if request.url.path == '/_bulk':
                return httpx.Response(200, json={'errors': True, 'items': [
                    {'index': {'status': 400, 'error': {'reason': 'private-server-details'}}},
                ]})
            return httpx.Response(200, json={})

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            async with PassageStore(client=client) as store:
                with self.assertRaises(SearchError) as error:
                    await import_passages([{'text': 'Chùa Thiên Mụ ở Huế.'}],
                                          store=store, embedder=vectors)
        self.assertNotIn('private-server-details', str(error.exception))

    async def test_invalid_batch_does_not_publish_any_documents(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: self.fail('invalid batch must not reach OpenSearch'),
        )) as client:
            async with PassageStore(client=client) as store:
                with self.assertRaises(ValueError):
                    await import_passages([{'text': 'valid'}, {'text': ' '}],
                                          store=store, embedder=vectors)

    async def test_search_failure_does_not_leak_dependency_body(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(503, text='password=private'),
        )) as client:
            async with PassageStore(client=client) as store:
                with self.assertRaises(SearchError) as error:
                    await PassageRepository(store, embedder=vectors).search_evidence('Thiên Mụ')
        self.assertNotIn('private', str(error.exception))


@unittest.skipUnless(os.environ.get('OPENSEARCH_TEST_URL'), 'local OpenSearch required')
class OpenSearchIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.index = 'heritage-test-' + uuid.uuid4().hex
        self.store = await PassageStore(url=os.environ['OPENSEARCH_TEST_URL'], index=self.index).__aenter__()

    async def asyncTearDown(self):
        await self.store.client.delete(f'{self.store.url}/{self.index}')
        await self.store.client.delete(f'{self.store.url}/_search/pipeline/{self.index}-hybrid')
        await self.store.__aexit__(None, None, None)

    async def test_ingest_search_and_repeat_need_neither_postgres_nor_r2(self):
        rows = [
            {'text': 'Chùa Thiên Mụ được dựng năm 1601 tại Huế.',
             'location_note': 'Chùa Thiên Mụ', 'source_url': 'https://example.org/thien-mu'},
            {'text': 'Bún bò Huế có mắm ruốc.', 'location_note': 'Bún bò Huế'},
        ]
        self.assertEqual(await import_passages(rows, store=self.store, embedder=vectors), 2)
        first = await self.store.export_passages(10)
        self.assertEqual(await import_passages(rows, store=self.store, embedder=vectors), 2)
        second = await self.store.export_passages(10)
        self.assertEqual({r['id'] for r in first}, {r['id'] for r in second})
        self.assertEqual(len(second), 2)
        with patch('apps.backend.core.storage.R2PassageStore', side_effect=AssertionError('no R2')):
            repo = PassageRepository(self.store, embedder=vectors)
            for question in ('Chùa Thiên Mụ xây năm nào?', 'chua thien mu xay nam nao?'):
                result = await repo.search_evidence(question, limit=1)
                self.assertEqual([e.text for e in result.evidence], [rows[0]['text']])
                self.assertEqual(result.evidence[0].to_source()['url'], rows[0]['source_url'])
            self.assertEqual((await repo.search_evidence(' ')).evidence, [])
            # Both lexical and vector branches must reject unrelated input.
            unrelated = PassageRepository(self.store,
                embedder=lambda texts: [[0.0, 0.0, 1.0] + [0.0] * 1021 for t in texts])
            self.assertEqual((await unrelated.search_evidence('zzqxv')).evidence, [])

    async def test_wrong_embedding_model_cannot_be_returned_by_either_channel(self):
        await self.store.ensure_index()
        await self.store.index_passages([{
            'id': 'stale', 'text': 'Chùa Thiên Mụ năm 9999.',
            'embedding': vectors(['Thiên Mụ'])[0], 'embedding_model': 'different-model',
            'content_hash': 'stale', 'passage_index': 0,
        }])
        result = await PassageRepository(self.store, embedder=vectors).search_evidence('Chùa Thiên Mụ')
        self.assertEqual(result.evidence, [])

    async def test_lexical_channel_survives_vector_miss_and_vector_channel_survives_lexical_miss(self):
        await import_passages([
            {'text': 'Chùa Thiên Mụ năm 1601.'},
            {'text': 'Món ăn miền Trung có mắm ruốc.'},
        ], store=self.store, embedder=vectors)
        # Orthogonal vectors cannot find the temple, so BM25 must supply it.
        lexical = PassageRepository(self.store,
            embedder=lambda texts: [[0.0, 0.0, 1.0] + [0.0] * 1021 for t in texts])
        self.assertIn('1601', (await lexical.search_evidence('chua thien mu', 1)).evidence[0].text)
        # No shared words: only the semantic vector can find the temple.
        semantic = PassageRepository(self.store, embedder=lambda texts: [vectors(['Thiên Mụ'])[0]])
        self.assertIn('1601', (await semantic.search_evidence('ancient pagoda', 1)).evidence[0].text)

    async def test_context_budget_preserves_whole_chunks(self):
        content = 'Chùa Thiên Mụ ở Huế. ' + 'Di sản văn hóa. ' * 120
        await import_passages([{'text': content, 'id': str(i)} for i in range(3)],
                              store=self.store, embedder=vectors)
        result = await PassageRepository(self.store, embedder=vectors).search_evidence('Chùa Thiên Mụ')
        self.assertTrue(result.evidence)
        self.assertLessEqual(sum(len(e.text) for e in result.evidence), 4800)
        self.assertTrue(all(e.text == content for e in result.evidence))


if __name__ == '__main__':
    unittest.main()
