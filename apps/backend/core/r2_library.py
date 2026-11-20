"""Knowledge operations on the existing R2 adapter and its SDK connection."""
import json
import codecs
import hashlib
import logging
import os
from tempfile import SpooledTemporaryFile
from pathlib import PurePosixPath
from urllib.parse import quote

from botocore.exceptions import BotoCoreError
from fastapi import HTTPException

from apps.backend.core.r2 import R2Storage
from apps.backend.services.knowledge_policy import (
    BUCKET, URL_SECONDS, UPLOAD_TYPES, library_path, new_name,
    preview_limit, staging_path,
)

log = logging.getLogger(__name__)


class KnowledgeR2(R2Storage):
    def __init__(self, *, client=None):
        if os.environ.get("R2_KNOWLEDGE_BUCKET", BUCKET) != BUCKET:
            raise HTTPException(503, "Knowledge library must use the configured knowledge-heritage bucket.")
        super().__init__(client=client, bucket=BUCKET)

    def call(self, method, **kwargs):
        try:
            return super().call(method, **kwargs)
        except HTTPException as error:
            # Do not log keys, credentials, signed URLs or provider error bodies.
            logger = log.warning if error.status_code >= 500 else log.debug
            logger("knowledge_storage_failure operation=%s status=%s", method, error.status_code)
            raise HTTPException(error.status_code, {
                404: "Knowledge object not found.",
                409: "Knowledge object already exists or changed; refresh the library.",
            }.get(error.status_code, "Knowledge storage unavailable.")) from None

    def list_objects(self, prefix, limit=100, cursor=None):
        prefix = library_path(prefix, prefix=True)
        options = {"Prefix": prefix, "Delimiter": "/", "MaxKeys": limit}
        if cursor:
            options["ContinuationToken"] = cursor
        page = self.call("list_objects_v2", **options)
        return {"bucket": BUCKET, "prefix": prefix,
                "folders": [{"name": row["Prefix"][len(prefix):].rstrip("/"), "prefix": row["Prefix"]}
                            for row in page.get("CommonPrefixes", []) if not staging_path(row["Prefix"])],
                "files": [{"name": row["Key"][len(prefix):], "key": row["Key"], "size": row["Size"],
                           "lastModified": row["LastModified"]} for row in page.get("Contents", [])
                          if row["Key"] != prefix and not row["Key"].endswith("/") and not staging_path(row["Key"])],
                "nextContinuationToken": page.get("NextContinuationToken")}

    def maybe_head(self, key):
        try:
            return self.call("head_object", Key=key)
        except HTTPException as error:
            if error.status_code == 404:
                return None
            raise

    @staticmethod
    def metadata(key, head):
        # Provider-defined user metadata may contain secrets. Explicit allowlist only.
        safe = {k: v for k, v in head.get("Metadata", {}).items() if k in {"language", "source-type"}}
        return {"bucket": BUCKET, "key": key, "name": key.rsplit("/", 1)[-1],
                "size": head["ContentLength"], "contentType": head.get("ContentType", "application/octet-stream"),
                "lastModified": head["LastModified"], "etag": head["ETag"], "metadata": safe}

    def object_info(self, key):
        key = library_path(key)
        return self.metadata(key, self.call("head_object", Key=key))

    def signed_url(self, method, params):
        try:
            return self.client.generate_presigned_url(method, Params={"Bucket": BUCKET, **params},
                                                       ExpiresIn=URL_SECONDS, HttpMethod={"put_object": "PUT", "get_object": "GET"}[method])
        except BotoCoreError:
            log.warning("knowledge_signing_failure operation=%s", method)
            raise HTTPException(503, "Cannot create a knowledge storage URL.") from None

    def upload_url(self, upload):
        headers = {"Content-Type": upload.content_type, "If-None-Match": "*",
                   "x-amz-meta-upload-id": upload.id}
        url = self.signed_url("put_object", {"Key": upload.staging_key, "ContentType": upload.content_type,
                              "ContentLength": upload.size_bytes, "IfNoneMatch": "*",
                              "Metadata": {"upload-id": upload.id}})
        # Content-Length is signed. Browsers set it from the exact File/Blob;
        # JavaScript must not try to set this forbidden request header itself.
        return {"uploadId": upload.id, "objectKey": upload.final_key, "uploadUrl": url,
                "expiresIn": URL_SECONDS, "sessionExpiresAt": upload.expires_at, "requiredHeaders": headers}

    def download(self, key):
        info = self.object_info(key)
        url = self.signed_url("get_object", {"Key": key,
            "ResponseContentDisposition": "attachment; filename*=UTF-8''" + quote(info["name"], safe=""),
            "ResponseContentType": "application/octet-stream"})
        return {"key": key, "downloadUrl": url, "expiresIn": URL_SECONDS}

    def preview(self, key):
        key = library_path(key)
        extension = PurePosixPath(key).suffix.lower()
        if extension not in UPLOAD_TYPES:
            raise HTTPException(415, "Preview supports .md, .txt and .json only.")
        head = self.call("head_object", Key=key)
        size, maximum = head["ContentLength"], preview_limit()
        if size > maximum:
            raise HTTPException(413, "Object exceeds the text preview limit; use download.")
        if size == 0:
            if extension == ".json":
                self.validate_json("")
            return {"key": key, "content": "", "size": 0, "etag": head["ETag"]}
        stream = self.call("get_object", Key=key, IfMatch=head["ETag"], Range=f"bytes=0-{maximum}")["Body"]
        try:
            raw = stream.read(maximum + 1)
        except (BotoCoreError, OSError):
            log.warning("knowledge_content_read_failure operation=preview")
            raise HTTPException(503, "Cannot read knowledge content.") from None
        finally:
            stream.close()
        if len(raw) > maximum:
            raise HTTPException(413, "Object exceeds the text preview limit.")
        if len(raw) != size:
            raise HTTPException(409, "Object changed or its content is incomplete.")
        text = self.decode_text(raw)
        if extension == ".json":
            self.validate_json(text)
        return {"key": key, "content": text, "size": size, "etag": head["ETag"]}

    @staticmethod
    def decode_text(raw):
        try:
            text = raw.decode("utf-8")
            if any(ord(c) < 32 and c not in "\r\n\t" for c in text):
                raise ValueError
            return text
        except (UnicodeDecodeError, ValueError):
            raise HTTPException(422, "Knowledge text must be valid UTF-8 without binary control bytes.") from None

    @staticmethod
    def validate_json(text):
        def reject_constant(value):
            raise ValueError(value)
        try:
            json.loads(text.removeprefix("\ufeff"), parse_constant=reject_constant)
        except (ValueError, RecursionError):
            raise HTTPException(422, "Knowledge JSON content is invalid.") from None

    def create_folder(self, parent_prefix, name):
        key = library_path(library_path(parent_prefix, prefix=True) + new_name(name) + "/", prefix=True)
        if self.call("list_objects_v2", Prefix=key, MaxKeys=1).get("Contents"):
            raise HTTPException(409, "Knowledge folder already exists.")
        # Also reject a file occupying the intended folder name.
        if self.maybe_head(key[:-1]) is not None:
            raise HTTPException(409, "A file already uses this folder name.")
        self.call("put_object", Key=key, Body=b"", ContentLength=0,
                  ContentType="application/x-directory", IfNoneMatch="*")
        return {"name": name, "prefix": key}

    def delete_file(self, key):
        key = library_path(key)
        self.call("head_object", Key=key)
        # Exactly one key. Never use DeleteObjects, prefix scans or marker deletion.
        self.call("delete_object", Key=key)

    @staticmethod
    def verify_identity(upload, head, *, published=False):
        if (head["ContentLength"] != upload.size_bytes
                or head.get("ContentType") != upload.content_type
                or head.get("ContentEncoding")
                or head.get("Metadata", {}).get("upload-id") != upload.id):
            raise HTTPException(422, "Object size, type or identity does not match this upload session.")
        if published and not head.get("Metadata", {}).get("content-sha256"):
            raise HTTPException(409, "Destination was not verified by this upload session.")

    def publish_verified(self, upload):
        """Bounded disk spool; validate all bytes before a create-only destination PUT."""
        head = self.call("head_object", Key=upload.staging_key)
        self.verify_identity(upload, head)
        stream = self.call("get_object", Key=upload.staging_key, IfMatch=head["ETag"])["Body"]
        with SpooledTemporaryFile(max_size=1024**2, mode="w+b") as spool:
            decoder, digest, total = codecs.getincrementaldecoder("utf-8")(), hashlib.sha256(), 0
            try:
                while True:
                    chunk = stream.read(min(65536, upload.size_bytes - total + 1))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > upload.size_bytes:
                        raise HTTPException(422, "Uploaded content exceeds the declared size.")
                    text = decoder.decode(chunk)
                    if any(ord(c) < 32 and c not in "\r\n\t" for c in text):
                        raise HTTPException(422, "Uploaded text contains binary control bytes.")
                    digest.update(chunk)
                    spool.write(chunk)
                decoder.decode(b"", final=True)
            except UnicodeDecodeError:
                raise HTTPException(422, "Uploaded text must use valid UTF-8.") from None
            except (BotoCoreError, OSError):
                log.warning("knowledge_content_read_failure operation=verify_upload")
                raise HTTPException(503, "Cannot verify knowledge upload content.") from None
            finally:
                stream.close()
            if total != upload.size_bytes:
                raise HTTPException(422, "Uploaded content is incomplete.")
            if PurePosixPath(upload.filename).suffix.lower() == ".json":
                spool.seek(0)
                self.validate_json(self.decode_text(spool.read()))
            spool.seek(0)
            self.call("put_object", Key=upload.final_key, Body=spool,
                      ContentLength=total, ContentType=upload.content_type, IfNoneMatch="*",
                      Metadata={"upload-id": upload.id, "content-sha256": digest.hexdigest()})
        result = self.call("head_object", Key=upload.final_key)
        self.verify_identity(upload, result, published=True)
        return result
