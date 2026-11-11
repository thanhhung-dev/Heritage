"""Ingestion metadata and embedding compatibility through the public importer."""
import importlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import AsyncMock, patch

from apps.backend.core.embedding import EMBEDDING_ID
from apps.backend.db.import_passages import import_passages
from apps.backend.tests.test_opensearch import vectors


class PassageImportTests(unittest.IsolatedAsyncioTestCase):
    async def test_transcript_metadata_survives_both_importers_without_changing_text_or_id(self):
        metadata = {'content_type': 'tour_script', 'heritage_slug': 'lang-tu-duc',
                    'active_area_id': 'lang-tu-duc', 'scene_id': 508,
                    'scene_key': 's5', 'language': 'vi'}
        text = '---\ncontent_type: tour_script\n---\n00:00:00s\nLời thuyết minh.'
        for name in ('apps.backend.db.import_passages', 'apps.backend.ai.ingestion.import_passages'):
            with self.subTest(module=name):
                store = AsyncMock()
                package = {'documents': [{'key': 'doc', **metadata}], 'passages': [
                    {'id': 'stable-script', 'document_key': 'doc', 'text': text,
                     'active_area_id': 'khiem-lang'}]}
                await importlib.import_module(name).import_passages(package, store=store, embedder=vectors)
                saved = store.index_passages.call_args.args[0][0]
                self.assertEqual({key: saved[key] for key in metadata},
                                 {**metadata, 'active_area_id': 'khiem-lang'})
                self.assertEqual((saved['id'], saved['text']), ('stable-script', text))

    async def test_invalid_tour_metadata_rejects_whole_batch_before_external_work(self):
        valid = {'content_type': 'tour_script', 'heritage_slug': 'lang-tu-duc',
                 'active_area_id': 'khiem-lang', 'scene_id': 508,
                 'scene_key': 's5', 'language': 'vi'}
        cases = [dict(valid, scene_id=value) for value in (True, 0, -1, '508', 2 ** 63)]
        cases += [dict(valid, scene_key=value) for value in ('s-1', 's05', 5)]
        cases += [dict(valid, language=''), dict(valid, language='vi_XX'),
                  dict(valid, heritage_slug='Lăng Tự Đức'), dict(valid, heritage_slug='lang-minh-mang'),
                  dict(valid, content_type='unknown'), dict(valid, active_area_id=None)]
        cases += [{key: value for key, value in valid.items() if key != missing}
                  for missing in valid]
        for name in ('apps.backend.db.import_passages', 'apps.backend.ai.ingestion.import_passages'):
            for metadata in cases:
                with self.subTest(module=name, metadata=metadata):
                    store = AsyncMock()
                    def no_embedding(texts):
                        self.fail('Invalid metadata must be rejected before embedding')
                    with self.assertRaises(ValueError):
                        await importlib.import_module(name).import_passages([
                            {'id': 'first', 'text': 'Dữ liệu hợp lệ.'},
                            {'id': 'invalid', 'text': '---\ncontent_type: tour_script\n---\nLời dẫn.',
                             **metadata}], store=store, embedder=no_embedding)
                    store.ensure_index.assert_not_awaited()
                    store.index_passages.assert_not_awaited()

    async def test_conflicting_document_and_passage_metadata_is_not_silently_overridden(self):
        metadata = {'content_type': 'tour_script', 'heritage_slug': 'lang-tu-duc',
                    'active_area_id': 'khiem-lang', 'scene_id': 508,
                    'scene_key': 's5', 'language': 'vi'}
        for name in ('apps.backend.db.import_passages', 'apps.backend.ai.ingestion.import_passages'):
            for field, value in (('scene_key', 's4'), ('scene_id', 506), ('language', 'en'),
                                 ('content_type', 'historical_source'),
                                 ('heritage_slug', 'tu-duc-tomb'), ('active_area_id', 'lang-minh-mang')):
                with self.subTest(module=name, field=field):
                    package = {'documents': [{'key': 'doc', **metadata}], 'passages': [
                        {'document_key': 'doc', 'text': 'Lời dẫn.', field: value}]}
                    with self.assertRaises(ValueError):
                        await importlib.import_module(name).import_passages(
                            package, store=AsyncMock(), embedder=vectors)

    def test_dry_run_cli_works_without_site_packages_or_external_services(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'package.json'
            for name in ('apps.backend.db.import_passages', 'apps.backend.ai.ingestion.import_passages'):
                script = {'id': 'script', 'text': 'Lời thuyết minh.', 'content_type': 'tour_script',
                          'heritage_slug': 'lang-tu-duc', 'active_area_id': 'lang-tu-duc',
                          'scene_id': 2 ** 63 - 1, 'scene_key': 's0', 'language': 'en-US'}
                cases = [([{'text': 'Khiêm Lăng, không có metadata tour.'}], 0, 'unclassified'),
                         ([script], 0, 'tour_script'),
                         ([{'text': '---\ncontent_type: tour_script\n---\nLời dẫn.'}], 1, None)]
                for payload, expected, content_type in cases:
                    path.write_text(json.dumps(payload), encoding='utf-8')
                    with self.subTest(module=name, expected=expected):
                        result = subprocess.run(
                            [sys.executable, '-S', '-m', name, str(path), '--dry-run',
                             '--env-file', str(Path(directory) / 'missing.env')],
                            capture_output=True, text=True, timeout=10)
                        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                        if expected == 0:
                            row = json.loads(result.stdout)['passages'][0]
                            self.assertEqual(row['content_type'], content_type)
                            if content_type == 'tour_script':
                                self.assertEqual(row['active_area_id'], 'khiem-lang')
                                self.assertEqual(row['scene_id'], 2 ** 63 - 1)
                            else:
                                self.assertNotIn('active_area_id', row)
                        else:
                            self.assertIn('content_type', result.stdout + result.stderr)
                        # Also exercise the CLI in a warm backend process: dry-run
                        # must remain offline even when dependencies are available.
                        with patch('sys.argv', [name, str(path), '--dry-run']), \
                                patch('socket.create_connection', side_effect=AssertionError('Network forbidden')), \
                                redirect_stdout(io.StringIO()) as output:
                            self.assertEqual(importlib.import_module(name).main(), expected)
                        if expected == 0:
                            self.assertEqual(json.loads(output.getvalue())['passages'][0]['content_type'],
                                             content_type)

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
        self.assertNotIn('active_area_id', row)
        self.assertNotIn('content_type', row)

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
