"""Download explicit R2 file URLs and build a reviewable PostgreSQL package.

No bucket scan, R2 write, database write, or model inference occurs here.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from apps.backend.core.corpus import chunk_text_spans
from apps.backend.db.import_structured import PackageValidationError, validate_package

MAX_BYTES = 16 * 1024 * 1024
PROCESSOR_VERSION = "r2-text-v1"


class IngestionError(ValueError):
    """Safe-to-display ingestion failure (never includes a download URL)."""


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _http_url(value: object, *, public: bool = False) -> bool:
    if not isinstance(value, str):
        return False
    try:
        url = urlsplit(value)
        return (url.scheme in {"http", "https"} and bool(url.hostname)
                and not url.username and not url.password
                and (not public or not (url.query or url.fragment)))
    except ValueError:
        return False


def _download(client: httpx.Client, url: str, max_bytes: int) -> tuple[bytes, str]:
    try:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            data = bytearray()
            for part in response.iter_bytes():
                data.extend(part)
                if len(data) > max_bytes:
                    raise IngestionError("File vượt giới hạn byte; tăng --max-bytes nếu cần.")
            return bytes(data), response.headers.get("content-type", "").split(";")[0].lower()
    except httpx.HTTPStatusError as exc:
        raise IngestionError(f"Tải file thất bại: HTTP {exc.response.status_code}.") from None
    except httpx.HTTPError:
        raise IngestionError("Không tải được file; kiểm tra kết nối/link và hạn signed URL.") from None


def _extract(data: bytes, kind: str) -> str:
    try:
        if kind == "pdf":
            reader = PdfReader(io.BytesIO(data))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            text = data.decode("utf-8-sig")
            if kind == "html":
                soup = BeautifulSoup(text, "html.parser")
                for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
                    tag.decompose()
                text = (soup.find("main") or soup.find("article") or soup).get_text("\n")
    except Exception:
        raise IngestionError("Không trích được text; kiểm tra định dạng/UTF-8/PDF mã hóa.") from None
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    text = "\n".join(re.sub(r"[^\S\n]+", " ", line).strip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text or "\x00" in text:
        raise IngestionError("Không có text hợp lệ; PDF scan/ảnh cần OCR trước ingestion.")
    return text


def run_ingestion(
    config: dict, output: Path, *, client: httpx.Client | None = None,
    max_bytes: int = MAX_BYTES,
) -> Path:
    """Build all artifacts before committing a local release directory.

    Repeating identical input is a no-op. Changed input must use a new version
    and output directory; failed downloads never leave a partial package.
    """
    if not isinstance(config, dict) or not isinstance(config.get("documents"), list):
        raise IngestionError("Config phải có documents là danh sách file.")
    version = config.get("corpus_version")
    if type(version) is not int or version < 1 or not config["documents"]:
        raise IngestionError("Cần corpus_version nguyên dương và ít nhất một document.")
    chunking = config.get("chunking", {"max_chars": 2400, "overlap_chars": 300})
    if (not isinstance(chunking, dict) or set(chunking) != {"max_chars", "overlap_chars"}
            or any(type(v) is not int for v in chunking.values())):
        raise IngestionError("chunking cần max_chars và overlap_chars là số nguyên.")
    try:
        chunk_text_spans("", **chunking)
    except ValueError as exc:
        raise IngestionError(str(exc)) from None
    if max_bytes <= 0:
        raise IngestionError("max_bytes phải > 0.")

    specs = []
    identities = set()
    for index, spec in enumerate(config["documents"]):
        if not isinstance(spec, dict):
            raise IngestionError(f"documents[{index}] phải là object.")
        url = spec.get("url") or os.environ.get(spec.get("url_env", ""), "")
        if not _http_url(url) or not _http_url(spec.get("source_url"), public=True):
            raise IngestionError(f"documents[{index}]: cần url tải HTTP(S) và source_url không chứa query/secret.")
        key = spec.get("object_key")
        if (not isinstance(key, str) or not key or key.startswith("/")
                or ".." in key.split("/") or "?" in key or "#" in key):
            raise IngestionError(f"documents[{index}]: object_key không hợp lệ.")
        if spec["source_url"] in identities:
            raise IngestionError(f"documents[{index}]: source_url trùng; mỗi nguồn phải có identity riêng.")
        identities.add(spec["source_url"])
        specs.append((spec, url))

    if client is None:
        with httpx.Client(timeout=60, follow_redirects=True) as owned_client:
            return run_ingestion(config, output, client=owned_client, max_bytes=max_bytes)

    processing = {"version": PROCESSOR_VERSION, "chunking": chunking,
                  "beautifulsoup4": __import__("bs4").__version__,
                  "pypdf": __import__("pypdf").__version__}
    digest = _hash(_json_bytes(processing))
    package = {"corpus_version": version, "release_status": "draft",
               "documents": [], "passages": [], "entities": [], "aliases": []}
    manifest = {"schema_version": 1, "corpus_version": version,
                "processing_config": processing, "processing_config_digest": digest,
                "search": "postgres-fts-trigram", "embedding_model": None,
                "objects": [], "documents": [], "passages": []}
    files: dict[str, bytes] = {}

    def artifact(path: str, data: bytes, object_key: str | None = None) -> None:
        files[path] = data
        manifest["objects"].append({"local_path": path, "object_key": object_key,
                                    "sha256": _hash(data), "size": len(data)})

    for index, (spec, url) in enumerate(specs):
        try:
            data, mime = _download(client, url, max_bytes)
            extension = Path(urlsplit(url).path).suffix.lower().lstrip(".")
            kind = spec.get("format") or extension or {
                "text/plain": "txt", "text/markdown": "md", "text/html": "html",
                "application/pdf": "pdf",
            }.get(mime)
            if kind not in {"txt", "md", "html", "pdf"}:
                raise IngestionError("Chỉ hỗ trợ txt, md, html, pdf; đặt format nếu link không có đuôi file.")
            text = _extract(data, kind)
            doc_key = "DOC-" + _hash(spec["source_url"].encode())
            content_hash = _hash(text.encode())
            doc = {field: spec.get(field) for field in (
                "title", "region", "source_url", "source_type", "tier", "observed_at",
            )}
            doc.update(key=doc_key, raw_text=text, content_hash=content_hash,
                       object_key=spec["object_key"], license=spec.get("license"))
            package["documents"].append(doc)
            raw_path = f"raw/{doc_key}/{_hash(data)}.{kind}"
            artifact(raw_path, data, spec["object_key"])
            manifest["documents"].append({"document_key": doc_key,
                                          "source_object_key": spec["object_key"],
                                          "raw_local_path": raw_path,
                                          "content_hash": content_hash})
            for passage_index, chunk in enumerate(chunk_text_spans(text, **chunking)):
                passage_key = "PSG-" + _hash(
                    f"{doc_key}:{content_hash}:{digest}:{chunk['char_start']}".encode())
                object_key = f"knowledge/processed/corpus-v{version}/passages/{doc_key}/{passage_key}.json"
                passage = dict(chunk, key=passage_key, document_key=doc_key,
                               passage_index=passage_index, passage_object_key=object_key,
                               source_object_key=spec["object_key"], corpus_version=version)
                package["passages"].append(passage)
                local_path = object_key.removeprefix("knowledge/")
                artifact(local_path, _json_bytes(passage), object_key)
                manifest["passages"].append({"passage_key": passage_key,
                                             "document_key": doc_key,
                                             "passage_object_key": object_key,
                                             "local_path": local_path})
        except IngestionError as exc:
            raise IngestionError(f"documents[{index}]: {exc}") from None

    try:
        validate_package(package)
    except PackageValidationError as exc:
        raise IngestionError(str(exc)) from None
    artifact("package.json", _json_bytes(package))
    files["manifest.json"] = _json_bytes(manifest)
    files["manifest.sha256"] = (_hash(files["manifest.json"]) + "\n").encode()
    output = Path(output)
    if output.exists():
        if all((output / path).is_file() and (output / path).read_bytes() == data
               for path, data in files.items()):
            return output / "package.json"
        raise IngestionError("Output đã tồn tại với dữ liệu khác; dùng corpus_version và output mới.")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".ingestion-", dir=output.parent))
    try:
        for path, data in files.items():
            target = staging / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return output / "package.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingestion local từ link file R2 → package + manifest")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="Mặc định data/ingestion/corpus-vN")
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        output = args.output or Path("data/ingestion") / f"corpus-v{config.get('corpus_version')}"
        path = run_ingestion(config, output, max_bytes=args.max_bytes)
    except (IngestionError, OSError, ValueError):
        # JSON/parser errors can contain user input; never echo download URLs.
        error = sys.exc_info()[1]
        message = str(error) if isinstance(error, IngestionError) else "Không đọc/ghi được config hoặc output; kiểm tra JSON và đường dẫn."
        print(f"Ingestion thất bại: {message}", file=sys.stderr)
        return 1
    package = json.loads(path.read_text())
    print(f"Hoàn tất: {len(package['documents'])} documents, {len(package['passages'])} passages.")
    print(f"Package (draft): {path}")
    print("Chưa ghi database/R2; xem docs/ingestion.md để review và import.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
