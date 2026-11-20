"""Verify a reviewed link against the current OpenSearch passage body and source."""
import hashlib


def matches_reviewed_passage(row: dict, link: dict[str, str]) -> bool:
    content = row.get("text")
    return (
        isinstance(content, str) and bool(content.strip())
        and row.get("content_hash") == link["content_hash"]
        and hashlib.sha256(content.encode()).hexdigest() == link["content_hash"]
        and row.get("object_key", "") == link["object_key"]
        and row.get("bucket", "") == link["bucket"]
    )
