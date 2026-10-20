"""Ingestion metadata and embedding compatibility through the public importer."""
import unittest
from unittest.mock import AsyncMock

from apps.backend.core.embedding import EMBEDDING_ID
from apps.backend.db.import_passages import import_passages
from apps.backend.tests.test_opensearch import vectors


class PassageImportTests(unittest.IsolatedAsyncioTestCase):
    async def test_package_preserves_source_and_stable_chunk_identity(self):
        store = AsyncMock()
        package = {'documents': [{'key': 'doc', 'title': 'Chùa Thiên Mụ',
                                  'source_url': 'https://example.org/temple',
                                  'object_key': 'raw/temple.pdf'}],
                   'passages': [{'key': 'PSG-1', 'document_key': 'doc',
                                 'text': 'Chùa Thiên Mụ ở Huế.', 'passage_index': 0}]}
        self.assertEqual(await import_passages(package, store=store, embedder=vectors), 1)
        row = store.index_passages.call_args.args[0][0]
        self.assertEqual(row['id'], 'PSG-1')
        self.assertEqual(row['text'], package['passages'][0]['text'])
        self.assertEqual(row['source_url'], package['documents'][0]['source_url'])
        self.assertEqual(row['location_note'], 'Chùa Thiên Mụ')
        self.assertEqual(row['object_key'], 'raw/temple.pdf')

    async def test_invalid_embeddings_are_rejected_before_any_index_writes(self):
        for vector in ([], [0.0] * 1024, [float('nan')] * 1024, [1.0] * 1023):
            with self.subTest(vector_length=len(vector)):
                store = AsyncMock()
                with self.assertRaises(ValueError):
                    await import_passages([{'text': 'Chùa Thiên Mụ'}], store=store,
                                          embedder=lambda texts: [vector])
                store.index_passages.assert_not_awaited()

    async def test_migration_preserves_id_and_rejects_incompatible_model(self):
        row = {'id': 42, 'text': 'Chùa Thiên Mụ', 'content_hash': 'legacy-r2-hash',
               'embedding': vectors(['Thiên Mụ'])[0], 'embedding_model': EMBEDDING_ID}
        store = AsyncMock()
        await import_passages([row], store=store, reuse_embeddings=True)
        saved = store.index_passages.call_args.args[0][0]
        self.assertEqual(saved['id'], '42')
        self.assertEqual(saved['content_hash'], 'legacy-r2-hash')
        self.assertEqual(saved['embedding'], row['embedding'])
        row['embedding_model'] = 'different-model'
        with self.assertRaises(ValueError):
            await import_passages([row], store=store, reuse_embeddings=True)
