import hashlib
import io
import json
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import httpx
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from pipelines.ingestion.package import validate_package
from pipelines.ingestion.ingest_r2 import IngestionError, main, run_ingestion


class R2IngestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "output"
        self.text = "# Khởi dựng\n\n" + " ".join(
            f"Chi tiết lịch sử số {i} được ghi trong tài liệu." for i in range(13)
        )
        self.config = {
            "corpus_version": 7,
            "chunking": {"max_chars": 180, "overlap_chars": 35},
            "documents": [{
                "url": "https://r2.example/knowledge/thien-mu.md?signature=SECRET",
                "object_key": "knowledge/curated/thien-mu.md",
                "source_url": "https://example.org/thien-mu",
                "title": "Lịch sử Thiên Mụ", "region": "hue",
                "source_type": "official", "tier": 1,
                "observed_at": "2026-10-14T00:00:00Z",
            }],
        }

    def client(self, body=None, status=200, content_type="text/markdown"):
        return httpx.Client(transport=httpx.MockTransport(
            lambda request: httpx.Response(
                status, content=(body if body is not None else self.text.encode()),
                headers={"content-type": content_type},
            )
        ))

    def test_download_to_valid_package_with_overlap_checksums_and_no_signature(self):
        with self.client() as client:
            package_path = run_ingestion(self.config, self.output, client=client)
        package = json.loads(package_path.read_text(encoding="utf-8"))
        validate_package(package)
        self.assertEqual(package["release_status"], "draft")
        doc = package["documents"][0]
        self.assertEqual(doc["raw_text"], self.text)
        passages = package["passages"]
        self.assertGreater(len(passages), 2)
        covered = set()
        for passage in passages:
            start, end = passage["char_start"], passage["char_end"]
            self.assertLessEqual(end - start, 180)
            self.assertEqual(passage["text"], self.text[start:end])
            covered.update(range(start, end))
        for previous, following in zip(passages, passages[1:]):
            self.assertGreater(following["char_start"], previous["char_start"])
            self.assertLess(following["char_start"], previous["char_end"])
        self.assertTrue(all(i in covered for i, c in enumerate(self.text) if not c.isspace()))
        manifest = json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["objects"]:
            data = (self.output / entry["local_path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])
            self.assertEqual(len(data), entry["size"])
        for file in self.output.rglob("*.json"):
            self.assertNotIn("SECRET", file.read_text(encoding="utf-8"))

    def test_repeated_run_is_identical_and_distinct_sources_are_not_deduplicated(self):
        second = dict(self.config["documents"][0],
                      source_url="https://example.org/other", object_key="knowledge/other.md")
        self.config["documents"].append(second)
        with self.client() as client:
            path = run_ingestion(self.config, self.output, client=client)
            before = {str(p.relative_to(self.output)): p.read_bytes()
                      for p in self.output.rglob("*") if p.is_file()}
            run_ingestion(self.config, self.output, client=client)
        after = {str(p.relative_to(self.output)): p.read_bytes()
                 for p in self.output.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        package = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(package["documents"]), 2)
        self.assertNotEqual(package["documents"][0]["key"], package["documents"][1]["key"])

    def test_html_excludes_scripts_and_navigation(self):
        self.config["documents"][0]["format"] = "html"
        with self.client(b"<nav>MENU</nav><h1>History</h1><p>Built in 1601.</p>"
                         b"<script>EVIL</script>", content_type="text/html") as client:
            path = run_ingestion(self.config, self.output, client=client)
        text = json.loads(path.read_text(encoding="utf-8"))["documents"][0]["raw_text"]
        self.assertIn("Built in 1601.", text)
        self.assertNotIn("MENU", text)
        self.assertNotIn("EVIL", text)

    def test_failure_does_not_publish_partial_output_or_leak_url(self):
        for status, body, limit in ((403, b"denied", 1000), (200, b"x" * 1001, 1000),
                                    (200, b"   ", 1000)):
            with self.subTest(status=status, size=len(body)):
                with self.client(body, status=status) as client:
                    with self.assertRaises(IngestionError) as error:
                        run_ingestion(self.config, self.output, client=client, max_bytes=limit)
                self.assertNotIn("SECRET", str(error.exception))
                self.assertFalse(self.output.exists())

    def test_invalid_chunking_and_duplicate_identity_are_rejected(self):
        self.config["chunking"]["overlap_chars"] = 180
        with self.client() as client, self.assertRaises(IngestionError):
            run_ingestion(self.config, self.output, client=client)
        self.config["chunking"]["overlap_chars"] = 35
        self.config["documents"].append(dict(self.config["documents"][0]))
        with self.client() as client, self.assertRaises(IngestionError):
            run_ingestion(self.config, self.output, client=client)

    def test_changed_content_cannot_overwrite_a_completed_release(self):
        with self.client() as client:
            path = run_ingestion(self.config, self.output, client=client)
        original = path.read_bytes()
        with self.client(b"A different historical document.") as client:
            with self.assertRaisesRegex(IngestionError, "corpus_version"):
                run_ingestion(self.config, self.output, client=client)
        self.assertEqual(path.read_bytes(), original)

    def test_pdf_text_extraction_and_scan_requires_ocr(self):
        writer = PdfWriter()
        page = writer.add_blank_page(width=300, height=300)
        self.config["documents"][0]["format"] = "pdf"
        blank = io.BytesIO()
        writer.write(blank)
        with self.client(blank.getvalue()) as client:
            with self.assertRaisesRegex(IngestionError, "OCR"):
                run_ingestion(self.config, self.output, client=client)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 20 200 Td (Built in 1601.) Tj ET")
        page[NameObject("/Contents")] = stream
        pdf = io.BytesIO()
        writer.write(pdf)
        with self.client(pdf.getvalue()) as client:
            path = run_ingestion(self.config, self.output, client=client)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["documents"][0]["raw_text"], "Built in 1601.")

    def test_cli_over_real_http_and_invalid_config_is_controlled(self):
        text = self.text.encode()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown")
                self.end_headers()
                self.wfile.write(text)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        config_path = Path(self.temp.name) / "config.json"
        self.config["documents"][0]["url"] = f"http://127.0.0.1:{server.server_port}/document.md"
        config_path.write_text(json.dumps(self.config))
        arguments = ["ingest_r2", "--config", str(config_path), "--output", str(self.output)]
        try:
            with patch("sys.argv", arguments), redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(main(), 0)
            self.assertIn("1 documents", stdout.getvalue())
            self.assertTrue((self.output / "package.json").exists())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        config_path.write_text("[]")
        with patch("sys.argv", arguments[:3]), redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(main(), 1)
        self.assertIn("Config", stderr.getvalue())

    def test_timeout_unsupported_format_and_invalid_metadata_leave_no_output(self):
        def timeout(request):
            raise httpx.ReadTimeout("SECRET", request=request)

        with httpx.Client(transport=httpx.MockTransport(timeout)) as client:
            with self.assertRaises(IngestionError) as error:
                run_ingestion(self.config, self.output, client=client)
        self.assertNotIn("SECRET", str(error.exception))
        self.config["documents"][0]["format"] = "docx"
        with self.client() as client, self.assertRaisesRegex(IngestionError, "hỗ trợ"):
            run_ingestion(self.config, self.output, client=client)
        self.config["documents"][0]["format"] = "txt"
        self.config["documents"][0]["region"] = "unknown"
        with self.client() as client, self.assertRaisesRegex(IngestionError, "region"):
            run_ingestion(self.config, self.output, client=client)
        self.assertFalse(self.output.exists())

    def test_long_unbroken_word_does_not_create_one_chunk_per_character(self):
        with self.client(b"x" * 1000) as client:
            path = run_ingestion(self.config, self.output, client=client)
        passages = json.loads(path.read_text(encoding="utf-8"))["passages"]
        self.assertLessEqual(len(passages), 8)
        self.assertEqual(passages[0]["char_start"], 0)
        self.assertEqual(passages[-1]["char_end"], 1000)
        self.assertTrue(all(len(p["text"]) <= 180 for p in passages))


if __name__ == "__main__":
    unittest.main()
