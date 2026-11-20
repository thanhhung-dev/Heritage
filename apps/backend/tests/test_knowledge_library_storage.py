import io
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import HTTPException

from apps.backend.core.r2 import R2Storage
from apps.backend.core.r2_library import KnowledgeR2
from apps.backend.services.knowledge_policy import library_path, new_name, upload_key
from apps.backend.tests.knowledge_library_support import MemoryR2


class KnowledgeStorageTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"R2_KNOWLEDGE_LIBRARY_PREFIX": "",
            "R2_KNOWLEDGE_BUCKET": "knowledge-heritage", "KNOWLEDGE_PREVIEW_MAX_BYTES": "131072"}))
        self.client = MemoryR2()
        self.storage = KnowledgeR2(client=self.client)

    def assert_status(self, status, operation, *args, **kwargs):
        with self.assertRaises(HTTPException) as error:
            operation(*args, **kwargs)
        self.assertEqual(status, error.exception.status_code)
        return error.exception

    def test_real_root_nested_empty_and_paginated_mapping_without_flattening(self):
        self.client.seed("area/child/readme.md")
        self.client.seed("area/intro.md")
        self.client.seed("area/")
        self.client.seed("root.json", b"{}", "application/json")
        self.client.seed("__knowledge_library_uploads__/private/stage.txt")
        root = self.storage.list_objects("", 1)
        pages = [root]
        while pages[-1]["nextContinuationToken"]:
            pages.append(self.storage.list_objects("", 1, pages[-1]["nextContinuationToken"]))
        self.assertEqual([f["prefix"] for p in pages for f in p["folders"]], ["area/"])
        self.assertEqual([f["key"] for p in pages for f in p["files"]], ["root.json"])
        nested = self.storage.list_objects("area/")
        self.assertEqual(nested["folders"], [{"name": "child", "prefix": "area/child/"}])
        self.assertEqual([f["name"] for f in nested["files"]], ["intro.md"])
        self.assertEqual(self.storage.list_objects("missing/")["files"], [])
        self.assertTrue(all(c[1]["Delimiter"] == "/" for c in self.client.calls if c[0] == "list"))
        self.assertFalse(any(c[0] == "get" for c in self.client.calls))

    def test_exact_legacy_unicode_is_preserved_and_new_names_require_nfc(self):
        key = "Việt Nam/tài liệu.txt"
        self.client.seed(key)
        self.assertEqual(self.storage.object_info(key)["key"], key)
        self.assert_status(422, new_name, "tài liệu.txt")
        self.assertEqual(new_name("Việt Nam.md"), "Việt Nam.md")

    def test_invalid_keys_names_scope_and_upload_policy(self):
        for key in ("", "/", "../x", "a/../x", "a//b", "a\\b", "https://x", "a%2fb", "a\x00b", "a\u202eb", "folder/"):
            with self.subTest(key=key):
                self.assert_status(422, library_path, key)
        for name in ("", " ", "../x", 'a"b.md', "a\n.md", "x" * 256, "a/b"):
            with self.subTest(name=name):
                self.assert_status(422, new_name, name)
        self.assert_status(422, upload_key, "", "unsafe.html", "text/html", 5)
        self.assert_status(422, upload_key, "", "x.md", "text/plain", 5)
        self.assert_status(422, upload_key, "", "x.md", "text/markdown", 33554433)
        with patch.dict(os.environ, {"R2_KNOWLEDGE_LIBRARY_PREFIX": "safe/"}):
            self.assert_status(422, library_path, "safe2/x.txt")
            self.assert_status(422, library_path, "safe/__knowledge_library_uploads__/x.txt")
            self.assertEqual(library_path("safe/a.txt"), "safe/a.txt")

    def test_bucket_config_cannot_target_other_buckets_and_legacy_storage_is_unchanged(self):
        with patch.dict(os.environ, {"R2_KNOWLEDGE_BUCKET": "heritage"}):
            self.assert_status(503, KnowledgeR2, client=self.client)
        for bucket in ("heritage", "heritage-scene"):
            with self.subTest(bucket=bucket), patch.dict(os.environ, {"R2_BUCKET": bucket}):
                self.assertEqual(R2Storage(client=object()).bucket, bucket)
                self.assertEqual(KnowledgeR2(client=self.client).bucket, "knowledge-heritage")

    def test_metadata_and_download_allowlist_and_signed_ttl(self):
        self.client.seed("folder/read me.md", b"text", "text/markdown", {"secret": "hide", "language": "vi"})
        info = self.storage.object_info("folder/read me.md")
        self.assertEqual(info["metadata"], {"language": "vi"})
        self.storage.download(info["key"])
        method, params, ttl, verb = self.client.signed[-1]
        self.assertEqual((method, ttl, verb), ("get_object", 300, "GET"))
        self.assertIn("read%20me.md", params["ResponseContentDisposition"])
        self.assertEqual(params["ResponseContentType"], "application/octet-stream")
        self.assert_status(404, self.storage.object_info, "absent.txt")

    def test_preview_returns_plain_text_without_html_rendering_and_closes_stream(self):
        raw = '<script>alert("test")</script>\nViệt Nam'.encode()
        self.client.seed("sample.md", raw, "text/markdown")
        self.assertEqual(self.storage.preview("sample.md")["content"], raw.decode())
        self.assertTrue(self.client.streams[-1].closed)
        self.assert_status(415, self.storage.preview, "sample.html")
        self.client.seed("large.txt", b"x" * 131073)
        self.assert_status(413, self.storage.preview, "large.txt")
        for key, body in (("nul.txt", b"a\x00"), ("bad.txt", b"\xff"), ("invalid.json", b"{x}"), ("nan.json", b"NaN")):
            self.client.seed(key, body)
            self.assert_status(422, self.storage.preview, key)
            self.assertTrue(self.client.streams[-1].closed)

    def test_preview_rejects_stream_size_mismatch(self):
        self.client.seed("x.txt", b"okay")
        self.client.get_bytes = b"x"
        self.assert_status(409, self.storage.preview, "x.txt")
        self.assertTrue(self.client.streams[-1].closed)

    def test_empty_legacy_text_preview_does_not_issue_invalid_range_get(self):
        self.client.seed("empty.txt", b"")
        self.assertEqual(self.storage.preview("empty.txt")["content"], "")
        self.assertFalse(any(c[0] == "get" for c in self.client.calls))

    def test_marker_conflict_and_exact_delete_preserve_siblings(self):
        self.storage.create_folder("", "test")
        self.assert_status(409, self.storage.create_folder, "", "test")
        self.client.seed("implicit/child.txt")
        self.assert_status(409, self.storage.create_folder, "", "implicit")
        self.client.seed("test/a.txt")
        self.client.seed("test/ab.txt")
        self.storage.delete_file("test/a.txt")
        self.assertIn("test/ab.txt", self.client.objects)
        self.assertIn("test/", self.client.objects)
        for key in ("", "/", "test/", "../test", "test//a"):
            self.assert_status(422, self.storage.delete_file, key)
        self.assertEqual([c for c in self.client.calls if c[0] == "delete"], [("delete", {"Key": "test/a.txt"})])

    def test_racing_marker_create_uses_atomic_condition(self):
        def race(key):
            self.client.seed(key, b"existing")
        self.client.before_put = race
        self.assert_status(409, self.storage.create_folder, "", "racing")
        self.assertEqual(self.client.objects["racing/"]["body"], b"existing")

    def test_provider_errors_are_sanitized(self):
        with patch.object(self.client, "list_objects_v2", side_effect=ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "SECRET"}}, "ListObjectsV2")):
            error = self.assert_status(503, self.storage.list_objects, "")
            self.assertNotIn("SECRET", error.detail)

    def test_real_boto_signer_binds_conditional_headers_and_exact_length(self):
        from types import SimpleNamespace
        client = boto3.client("s3", endpoint_url="https://r2.example.invalid", region_name="auto",
            aws_access_key_id="synthetic-access", aws_secret_access_key="synthetic-secret",
            config=Config(signature_version="s3v4"))
        self.addCleanup(client.close)
        result = KnowledgeR2(client=client).upload_url(SimpleNamespace(id="test-id", staging_key="stage/test.txt",
            final_key="test.txt", content_type="text/plain", size_bytes=4, expires_at=None))
        query = parse_qs(urlsplit(result["uploadUrl"]).query)
        self.assertEqual(query["X-Amz-Expires"], ["300"])
        signed = query["X-Amz-SignedHeaders"][0].split(";")
        for header in ("content-length", "content-type", "if-none-match", "x-amz-meta-upload-id"):
            self.assertIn(header, signed)

    def test_real_sdk_accepts_atomic_publish_protocol_without_copy_or_network(self):
        import hashlib
        from datetime import datetime, timezone
        from types import SimpleNamespace
        from botocore.response import StreamingBody
        from botocore.stub import ANY, Stubber
        client = boto3.client("s3", endpoint_url="https://r2.example.invalid", region_name="auto",
            aws_access_key_id="synthetic-access", aws_secret_access_key="synthetic-secret",
            config=Config(signature_version="s3v4"))
        self.addCleanup(client.close)
        raw = b"hello"
        upload = SimpleNamespace(id="test-id", staging_key="stage/test.txt", final_key="test.txt",
            filename="test.txt", content_type="text/plain", size_bytes=len(raw))
        marker = {"upload-id": upload.id}
        published_marker = {**marker, "content-sha256": hashlib.sha256(raw).hexdigest()}
        head = {"ContentLength": len(raw), "ContentType": "text/plain", "ETag": '"etag"',
                "LastModified": datetime.now(timezone.utc), "Metadata": marker}
        with Stubber(client) as stub:
            stub.add_response("head_object", head, {"Bucket": "knowledge-heritage", "Key": upload.staging_key})
            stub.add_response("get_object", {"Body": StreamingBody(io.BytesIO(raw), len(raw))},
                {"Bucket": "knowledge-heritage", "Key": upload.staging_key, "IfMatch": head["ETag"]})
            stub.add_response("put_object", {"ETag": head["ETag"]}, {"Bucket": "knowledge-heritage",
                "Key": upload.final_key, "Body": ANY, "ContentLength": len(raw), "ContentType": "text/plain",
                "IfNoneMatch": "*", "Metadata": published_marker})
            stub.add_response("head_object", {**head, "Metadata": published_marker},
                {"Bucket": "knowledge-heritage", "Key": upload.final_key})
            self.assertEqual(KnowledgeR2(client=client).publish_verified(upload)["ContentLength"], len(raw))
            stub.assert_no_pending_responses()


if __name__ == "__main__":
    unittest.main()
