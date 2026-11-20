"""Central, exact-key policy for the private knowledge library."""
import os
import unicodedata
from pathlib import PurePosixPath

from fastapi import HTTPException

BUCKET = "knowledge-heritage"
STAGING = "__knowledge_library_uploads__/"
URL_SECONDS = 300
SESSION_SECONDS = 900
UPLOAD_TYPES = {".md": "text/markdown", ".txt": "text/plain", ".json": "application/json"}


def configured_limit(name: str, default: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
        if not 1 <= value <= maximum:
            raise ValueError
        return value
    except ValueError:
        raise HTTPException(503, "Invalid knowledge library size configuration.") from None


def upload_limit() -> int:
    return configured_limit("KNOWLEDGE_MAX_UPLOAD_BYTES", 10 * 1024**2, 32 * 1024**2)


def preview_limit() -> int:
    return configured_limit("KNOWLEDGE_PREVIEW_MAX_BYTES", 128 * 1024, 1024**2)


def _path(value: str, *, prefix: bool) -> str:
    # Never decode, strip, normalize, or join a client key into a different key.
    try:
        invalid = (len(value.encode("utf-8")) > 1024 or value.startswith("/")
                   or any(c in value for c in "\\%:")
                   or any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in value))
    except UnicodeEncodeError:
        invalid = True
    parts = value[:-1].split("/") if prefix and value.endswith("/") else value.split("/")
    if value and (any(p in {"", ".", ".."} for p in parts) or (prefix != value.endswith("/"))):
        invalid = True
    if not prefix and not value:
        invalid = True
    if invalid:
        raise HTTPException(422, "Invalid exact object key or slash-terminated prefix.")
    return value


def root_prefix() -> str:
    try:
        root = _path(os.environ.get("R2_KNOWLEDGE_LIBRARY_PREFIX", ""), prefix=True)
        if STAGING in root:
            raise ValueError
        return root
    except (HTTPException, ValueError):
        raise HTTPException(503, "Invalid knowledge library scope configuration.") from None


def library_path(value: str, *, prefix: bool = False) -> str:
    value = _path(value, prefix=prefix)
    root = root_prefix()
    if not value.startswith(root) or value.startswith(root + STAGING):
        raise HTTPException(422, "Path is outside the allowed library scope.")
    return value


def new_name(value: str) -> str:
    try:
        invalid = (not value or value != value.strip() or value in {".", ".."}
                   or value != unicodedata.normalize("NFC", value)
                   or len(value.encode("utf-8")) > 255
                   or any(c in value for c in '/\\%?#":*<>|')
                   or any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in value))
    except UnicodeEncodeError:
        invalid = True
    if invalid:
        raise HTTPException(422, "Use a single NFC Unicode filename without path or control characters.")
    return value


def upload_key(folder: str, filename: str, content_type: str, size: int) -> str:
    key = library_path(library_path(folder, prefix=True) + new_name(filename))
    if UPLOAD_TYPES.get(PurePosixPath(filename).suffix.lower()) != content_type:
        raise HTTPException(422, "Supported uploads: .md text/markdown, .txt text/plain, .json application/json.")
    if not 0 < size <= upload_limit():
        raise HTTPException(422, "Upload size is outside the configured limit.")
    return key
