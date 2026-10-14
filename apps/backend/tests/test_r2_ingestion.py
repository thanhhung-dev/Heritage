import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import httpx

from apps.backend.db.import_structured import validate_package
from pipelines.ingestion.ingest_r2 import IngestionError, run_ingestion


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
        package = json.loads(package_path.read_text())
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
        manifest = json.loads((self.output / "manifest.json").read_text())
        for entry in manifest["objects"]:
            data = (self.output / entry["local_path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])
            self.assertEqual(len(data), entry["size"])
        for file in self.output.rglob("*.json"):
            self.assertNotIn("SECRET", file.read_text())

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
        package = json.loads(path.read_text())
        self.assertEqual(len(package["documents"]), 2)
        self.assertNotEqual(package["documents"][0]["key"], package["documents"][1]["key"])

    def test_html_excludes_scripts_and_navigation(self):
        self.config["documents"][0]["format"] = "html"
        with self.client(b"<nav>MENU</nav><h1>History</h1><p>Built in 1601.</p>"
                         b"<script>EVIL</script>", content_type="text/html") as client:
            path = run_ingestion(self.config, self.output, client=client)
        text = json.loads(path.read_text())["documents"][0]["raw_text"]
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


if __name__ == "__main__":
    unittest.main()
