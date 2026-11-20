"""Synthetic S3 fixture. No production keys, credentials or network access."""
import hashlib
import io
import threading
from datetime import datetime, timezone

from botocore.exceptions import ClientError


class MemoryR2:
    def __init__(self):
        self.objects, self.calls, self.signed, self.streams = {}, [], [], []
        self.lock = threading.RLock()
        self.before_put = None
        self.get_bytes = None

    def record(self, method, bucket, **kwargs):
        assert bucket == "knowledge-heritage", "Library escaped its fixed bucket"
        self.calls.append((method, kwargs))

    @staticmethod
    def error(code, operation):
        raise ClientError({"Error": {"Code": code, "Message": "private provider detail"}}, operation)

    def put_object(self, Bucket, Key, Body=b"", ContentType="application/octet-stream", Metadata=None,
                   IfNoneMatch=None, ContentLength=None, **kwargs):
        self.record("put", Bucket, Key=Key, IfNoneMatch=IfNoneMatch)
        with self.lock:
            if self.before_put:
                callback, self.before_put = self.before_put, None
                callback(Key)
            if IfNoneMatch == "*" and Key in self.objects:
                self.error("PreconditionFailed", "PutObject")
            raw = Body.read() if hasattr(Body, "read") else Body
            if ContentLength is not None:
                assert ContentLength == len(raw)
            self.objects[Key] = {"body": raw, "ContentType": ContentType, "Metadata": Metadata or {},
                "ContentLength": len(raw), "ETag": '"' + hashlib.sha256(raw).hexdigest() + '"',
                "LastModified": datetime.now(timezone.utc), **kwargs}
            return {"ETag": self.objects[Key]["ETag"]}

    def seed(self, key, body=b"test", content_type="text/plain", metadata=None):
        self.put_object(Bucket="knowledge-heritage", Key=key, Body=body,
                        ContentType=content_type, Metadata=metadata)

    def head_object(self, Bucket, Key):
        self.record("head", Bucket, Key=Key)
        with self.lock:
            if Key not in self.objects:
                self.error("NoSuchKey", "HeadObject")
            return {k: v for k, v in self.objects[Key].items() if k != "body"}

    def get_object(self, Bucket, Key, IfMatch=None, Range=None):
        self.record("get", Bucket, Key=Key, IfMatch=IfMatch, Range=Range)
        head = self.head_object(Bucket, Key)
        if IfMatch and IfMatch != head["ETag"]:
            self.error("PreconditionFailed", "GetObject")
        raw = self.objects[Key]["body"] if self.get_bytes is None else self.get_bytes
        if Range:
            raw = raw[:int(Range.split("-")[1]) + 1]
        stream = io.BytesIO(raw)
        self.streams.append(stream)
        return {**head, "Body": stream}

    def list_objects_v2(self, Bucket, Prefix="", Delimiter=None, MaxKeys=1000, ContinuationToken=None):
        self.record("list", Bucket, Prefix=Prefix, Delimiter=Delimiter, MaxKeys=MaxKeys,
                    ContinuationToken=ContinuationToken)
        folders, files = set(), []
        for key, obj in sorted(self.objects.items()):
            if not key.startswith(Prefix):
                continue
            rest = key[len(Prefix):]
            if Delimiter and "/" in rest:
                folders.add(Prefix + rest.split("/")[0] + "/")
            else:
                files.append({"Key": key, "Size": obj["ContentLength"], "LastModified": obj["LastModified"]})
        entries = [("folder", p) for p in sorted(folders)] + [("file", p) for p in files]
        start = int(ContinuationToken or "0")
        page = entries[start:start + MaxKeys]
        truncated = start + MaxKeys < len(entries)
        return {"CommonPrefixes": [{"Prefix": p} for kind, p in page if kind == "folder"],
            "Contents": [p for kind, p in page if kind == "file"], "IsTruncated": truncated,
            **({"NextContinuationToken": str(start + MaxKeys)} if truncated else {})}

    def delete_object(self, Bucket, Key):
        self.record("delete", Bucket, Key=Key)
        self.objects.pop(Key, None)
        return {}

    def generate_presigned_url(self, method, Params, ExpiresIn, HttpMethod):
        assert Params["Bucket"] == "knowledge-heritage"
        self.signed.append((method, Params, ExpiresIn, HttpMethod))
        return "https://storage.example.invalid/synthetic-signed-url"

    def close(self):
        pass
