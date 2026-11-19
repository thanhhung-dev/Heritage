"""Parser behavior and backend-only packaging; no models, storage or network."""
import builtins
import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from apps.backend.core.document_text import IngestionError, extract_text
from apps.backend.services.reindex_worker import read_document


class DocumentTextTests(unittest.TestCase):
    def test_normalizes_utf8_bom_unicode_and_line_endings(self):
        text = extract_text('\ufeffDiêu\t khắc\r\n\r\n\r\nDi sản'.encode(), "md")
        self.assertEqual(text, 'Diêu khắc\n\nDi sản')

    def test_html_preserves_main_text_and_removes_executable_navigation(self):
        raw = b'<nav>Navigation</nav><main><h1>Heritage</h1><script>secret()</script><p>History</p></main>'
        self.assertEqual(extract_text(raw, "html"), "Heritage\nHistory")

    def test_invalid_format_encoding_empty_pdf_and_nul_fail_closed(self):
        for body, kind in ((b'content', 'exe'), (b'\xff', 'txt'), (b' ', 'md'), (b'x\0y', 'txt'), (b'invalid', 'pdf')):
            with self.subTest(kind=kind), self.assertRaises(IngestionError):
                extract_text(body, kind)

    def test_worker_reads_text_without_offline_pipeline_package(self):
        original_import = builtins.__import__
        def backend_only(name, *args, **kwargs):
            if name == 'pipelines' or name.startswith('pipelines.'):
                raise ModuleNotFoundError('pipelines is intentionally absent from the backend image')
            return original_import(name, *args, **kwargs)
        body = io.BytesIO(b'Heritage history')
        storage = SimpleNamespace(call=lambda *args, **kwargs: {'Body': body, 'ContentLength': 16})
        document = SimpleNamespace(size_bytes=16, object_key='curated/history.txt', etag='etag', filename='history.txt')
        with patch('builtins.__import__', side_effect=backend_only):
            self.assertEqual(read_document(storage, document), 'Heritage history')
        self.assertTrue(body.closed)
