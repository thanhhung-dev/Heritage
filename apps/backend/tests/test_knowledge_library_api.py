import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.backend.api.knowledge_dependencies import library_db, library_storage
from apps.backend.api.knowledge_library import router
from apps.backend.core import security
from apps.backend.core.r2_library import KnowledgeR2
from apps.backend.models.knowledge_library import LibraryUpload
from apps.backend.tests.knowledge_library_support import MemoryR2

BASE = "/api/admin/knowledge"


class KnowledgeLibraryApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.enterContext(patch.dict(os.environ, {"R2_KNOWLEDGE_BUCKET": "knowledge-heritage",
            "R2_KNOWLEDGE_LIBRARY_PREFIX": "", "KNOWLEDGE_MAX_UPLOAD_BYTES": "10485760"}))
        self.enterContext(patch.object(security, "SECRET_KEY", "synthetic-private-test-key-1234567890"))
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.addAsyncCleanup(self.engine.dispose)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(LibraryUpload.__table__.create)
            await conn.execute(text("CREATE TABLE roles(id INTEGER PRIMARY KEY,name TEXT)"))
            await conn.execute(text("CREATE TABLE account(id INTEGER PRIMARY KEY,role_id INTEGER,is_active BOOLEAN,locked_until TIMESTAMP)"))
            await conn.execute(text("INSERT INTO roles VALUES(1,'ADMIN'),(2,'USER')"))
            await conn.execute(text("INSERT INTO account VALUES(1,1,true,null),(2,2,true,null),(3,1,false,null),(4,1,true,'2099-01-01'),(5,1,true,null)"))
        app = FastAPI()
        app.include_router(router, prefix="/api")
        async def db_override():
            async with self.factory() as db:
                yield db
        self.s3 = MemoryR2()
        self.storage = KnowledgeR2(client=self.s3)
        app.dependency_overrides[library_db] = db_override
        app.dependency_overrides[library_storage] = lambda: self.storage
        self.app = app
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)
        self.auth = self.token()

    def token(self, actor="1", role="ADMIN", **claims):
        return {"Authorization": "Bearer " + security.create_access_token({"sub": actor, "role": role, **claims})}

    async def request(self, method, path, *, auth=True, **kwargs):
        if auth:
            kwargs.setdefault("headers", self.auth)
        return await self.client.request(method, BASE + path, **kwargs)

    async def begin(self, filename="test.md", raw=b"hello", content_type="text/markdown", folder="samples/"):
        response = await self.request("POST", "/upload-url", json={"folder": folder, "filename": filename,
            "contentType": content_type, "size": len(raw)})
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        async with self.factory() as db:
            upload = await db.get(LibraryUpload, result["uploadId"])
        self.s3.seed(upload.staging_key, raw, content_type, {"upload-id": upload.id})
        return result, upload

    async def test_every_route_rejects_missing_and_nonadmin_authentication_before_storage(self):
        endpoints = [("GET", "/objects", {}), ("GET", "/object?key=x.txt", {}),
            ("GET", "/preview?key=x.txt", {}), ("POST", "/download-url", {"key": "x.txt"}),
            ("POST", "/folders", {"parentPrefix": "", "folderName": "x"}),
            ("DELETE", "/objects", {"key": "x.txt"}),
            ("POST", "/upload-url", {"folder": "", "filename": "x.txt", "contentType": "text/plain", "size": 4}),
            ("POST", "/uploads/00000000-0000-0000-0000-000000000000/complete", {})]
        for method, path, body in endpoints:
            for headers, expected in (({}, 401), (self.token("2", "USER"), 403)):
                with self.subTest(method=method, path=path, status=expected):
                    result = await self.request(method, path, auth=False, headers=headers,
                                                **({"json": body} if method != "GET" else {}))
                    self.assertEqual(result.status_code, expected, result.text)
        self.assertEqual(self.s3.calls, [])

    async def test_rechecks_account_state_role_and_token_purpose(self):
        for auth, expected in ((self.token("2"), 403), (self.token("3"), 401), (self.token("4"), 401),
                (self.token("999"), 401), (self.token("-1"), 401), (self.token("1", type="reset"), 401),
                ({"Authorization": "Bearer garbage"}, 401)):
            with self.subTest(expected=expected):
                result = await self.request("GET", "/objects", auth=False, headers=auth)
                self.assertEqual(result.status_code, expected, result.text)
        with patch.object(security, "SECRET_KEY", "your-secret-key-change-this-in-production"):
            self.assertEqual((await self.request("GET", "/objects")).status_code, 503)

    async def test_listing_metadata_preview_download_headers_and_openapi_contract(self):
        self.s3.seed("folder/readme.md", "Xin chào".encode(), "text/markdown")
        listed = await self.request("GET", "/objects?prefix=folder/&limit=1")
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["files"][0]["name"], "readme.md")
        for path in ("/objects", "/object?key=folder/readme.md", "/preview?key=folder/readme.md"):
            response = await self.request("GET", path)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")
            self.assertIn("application/json", response.headers["content-type"])
        self.assertEqual((await self.request("POST", "/download-url", json={"key": "folder/readme.md"})).status_code, 200)
        self.assertEqual((await self.request("GET", "/objects?limit=1001")).status_code, 422)
        self.assertEqual((await self.request("GET", "/objects?prefix=../")).status_code, 422)
        schema = self.app.openapi()
        self.assertEqual(len([p for p in schema["paths"] if p.startswith(BASE)]), 7)
        for operations in schema["paths"].values():
            for operation in operations.values():
                self.assertTrue(operation["security"])

    async def test_upload_complete_is_durable_and_idempotent_and_staging_is_immutable(self):
        result, upload = await self.begin(raw="Việt Nam\n".encode())
        self.assertEqual(result["objectKey"], "samples/test.md")
        self.assertEqual(result["expiresIn"], 300)
        self.assertEqual(result["requiredHeaders"]["If-None-Match"], "*")
        self.assertEqual(self.s3.signed[-1][1]["ContentLength"], upload.size_bytes)
        for _ in range(2):
            response = await self.request("POST", f"/uploads/{upload.id}/complete")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["status"], "stored")
            self.assertEqual(response.json()["object"]["key"], upload.final_key)
        self.assertEqual(len([c for c in self.s3.calls if c[0] == "put" and c[1]["Key"] == upload.final_key]), 1)
        self.assertTrue(all(stream.closed for stream in self.s3.streams))
        async with self.factory() as db:
            record = await db.get(LibraryUpload, upload.id)
            self.assertEqual(record.status, "COMPLETED")
            self.assertIsNone(record.reservation_key)

    async def test_duplicate_filename_existing_object_or_active_session_never_overwrites(self):
        _, upload = await self.begin()
        payload = {"folder": "samples/", "filename": "test.md", "contentType": "text/markdown", "size": 5}
        self.assertEqual((await self.request("POST", "/upload-url", json=payload)).status_code, 409)
        self.s3.seed(upload.final_key, b"old object", "text/markdown")
        complete = await self.request("POST", f"/uploads/{upload.id}/complete")
        self.assertEqual(complete.status_code, 409)
        self.assertEqual(self.s3.objects[upload.final_key]["body"], b"old object")
        self.assertEqual((await self.request("POST", "/upload-url", json=payload)).status_code, 409)

    async def test_atomic_publish_rejects_an_external_writer_after_head(self):
        _, upload = await self.begin()
        self.s3.before_put = lambda key: self.s3.seed(key, b"external", "text/markdown")
        response = await self.request("POST", f"/uploads/{upload.id}/complete")
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.s3.objects[upload.final_key]["body"], b"external")

    async def test_expired_session_releases_reservation_and_cannot_publish(self):
        _, upload = await self.begin()
        async with self.factory() as db:
            await db.execute(update(LibraryUpload).where(LibraryUpload.id == upload.id).values(
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
            await db.commit()
        self.assertEqual((await self.request("POST", f"/uploads/{upload.id}/complete")).status_code, 410)
        self.assertNotIn(upload.final_key, self.s3.objects)
        result, second = await self.begin()
        self.assertNotEqual(result["uploadId"], upload.id)

    async def test_missing_upload_body_missing_session_and_wrong_owner(self):
        _, upload = await self.begin()
        wrong_owner = await self.request("POST", f"/uploads/{upload.id}/complete", auth=False, headers=self.token("5"))
        self.assertEqual(wrong_owner.status_code, 403)
        self.s3.objects.pop(upload.staging_key)
        self.assertEqual((await self.request("POST", f"/uploads/{upload.id}/complete")).status_code, 404)
        self.assertEqual((await self.request("POST", "/uploads/00000000-0000-0000-0000-000000000000/complete")).status_code, 404)
        self.assertEqual((await self.request("POST", "/uploads/not-a-uuid/complete")).status_code, 422)

    async def test_size_type_identity_content_and_full_file_validation(self):
        cases = [(b"good\xff", "text/markdown", None), (b"nul\x00x", "text/markdown", None),
                 (b"{bad}", "application/json", None), (b"NaN", "application/json", None),
                 (b"short", "text/markdown", "size"), (b"okay!", "text/markdown", "type"),
                 (b"okay!", "text/markdown", "identity"),
                 (b"x" * 70000 + b"\xff", "text/markdown", None)]
        for index, (raw, mime, tamper) in enumerate(cases):
            filename = f"case{index}" + (".json" if mime == "application/json" else ".md")
            _, upload = await self.begin(filename, raw, mime)
            obj = self.s3.objects[upload.staging_key]
            if tamper == "size":
                obj["ContentLength"] += 1
            elif tamper == "type":
                obj["ContentType"] = "application/octet-stream"
            elif tamper == "identity":
                obj["Metadata"] = {"upload-id": "wrong"}
            with self.subTest(case=index):
                response = await self.request("POST", f"/uploads/{upload.id}/complete")
                self.assertEqual(response.status_code, 422, response.text)
                self.assertNotIn(upload.final_key, self.s3.objects)

    async def test_recover_successful_publish_after_lost_database_commit(self):
        _, upload = await self.begin(filename="recovery.json", raw=b'{"a":1}', content_type="application/json")
        self.storage.publish_verified(upload)
        async with self.factory() as db:
            self.assertEqual((await db.get(LibraryUpload, upload.id)).status, "PENDING")
        response = await self.request("POST", f"/uploads/{upload.id}/complete")
        self.assertEqual(response.status_code, 200, response.text)
        self.s3.objects.pop(upload.final_key)
        self.assertEqual((await self.request("POST", f"/uploads/{upload.id}/complete")).status_code, 404)
        self.assertNotIn(upload.final_key, self.s3.objects)

    async def test_write_validation_rejects_extra_bucket_recursive_flags_and_bad_files(self):
        default = {"folder": "", "filename": "test.md", "contentType": "text/markdown", "size": 5}
        for changes in ({"bucket": "heritage"}, {"size": True}, {"size": 10485761}, {"filename": "../x.md"},
                {"contentType": "text/html"}, {"folder": "../"}, {"size": 0}, {"filename": "x.pdf"}):
            with self.subTest(changes=changes):
                response = await self.request("POST", "/upload-url", json={**default, **changes})
                self.assertEqual(response.status_code, 422, response.text)
        for body in ({"key": ""}, {"key": "/"}, {"key": "folder/"}, {"key": "x.txt", "recursive": True},
                     {"key": "x.txt", "bucket": "heritage"}):
            self.assertEqual((await self.request("DELETE", "/objects", json=body)).status_code, 422)

    async def test_folder_and_delete_http_contract(self):
        created = await self.request("POST", "/folders", json={"parentPrefix": "", "folderName": "manual"})
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["prefix"], "manual/")
        self.s3.seed("manual/a.txt")
        deleted = await self.request("DELETE", "/objects", json={"key": "manual/a.txt"})
        self.assertEqual(deleted.status_code, 204, deleted.text)
        self.assertEqual(deleted.content, b"")
        self.assertEqual((await self.request("DELETE", "/objects", json={"key": "manual/a.txt"})).status_code, 404)
        self.assertIn("manual/", self.s3.objects)

    async def test_key_byte_limits_include_server_generated_staging_path(self):
        result, upload = await self.begin(filename="b" * 252 + ".md", folder="a" * 768 + "/")
        self.assertEqual(len(upload.final_key.encode()), 1024)
        self.assertTrue(all(len(c[1].get("Key", c[1].get("Prefix", "")).encode()) <= 1024 for c in self.s3.calls))
        with patch.dict(os.environ, {"R2_KNOWLEDGE_LIBRARY_PREFIX": "a" * 980 + "/"}):
            response = await self.request("POST", "/upload-url", json={"folder": "a" * 980 + "/",
                "filename": "x.txt", "contentType": "text/plain", "size": 5})
            self.assertEqual(response.status_code, 422, response.text)

    async def test_multibyte_text_across_stream_boundary_and_changed_completed_object(self):
        raw = b"x" * 65535 + "ệ Việt Nam".encode()
        _, upload = await self.begin(raw=raw)
        response = await self.request("POST", f"/uploads/{upload.id}/complete")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.s3.objects[upload.final_key]["body"], raw)
        self.s3.objects[upload.final_key]["ETag"] = '"changed"'
        self.assertEqual((await self.request("POST", f"/uploads/{upload.id}/complete")).status_code, 409)

    async def test_tokens_require_finite_expiry_and_valid_subject(self):
        import jwt
        for changes in ({"exp": float("inf")}, {"exp": float("nan")}, {"exp": 0}, {"exp": None},
                        {"sub": "9223372036854775808"}, {"sub": "not-an-id"}):
            claims = {"sub": "1", "role": "ADMIN", "exp": datetime.now(timezone.utc).timestamp() + 60, **changes}
            encoded = jwt.encode(claims, security.SECRET_KEY, algorithm=security.ALGORITHM)
            response = await self.request("GET", "/objects", auth=False, headers={"Authorization": "Bearer " + encoded})
            self.assertEqual(response.status_code, 401, response.text)


if __name__ == "__main__":
    unittest.main()
