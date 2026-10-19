"""Validate provenance and exact source spans in ingestion packages."""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

_SOURCE_TYPES = {"official", "academic", "management", "press", "encyclopedia", "other"}
_ENTITY_TYPES = {"person", "place", "event", "artifact"}
_ALIAS_TYPES = {"official", "historical", "common", "sino_vietnamese", "english", "typo"}
_ENTRY_STATUSES = {"draft", "reviewed", "published", "withdrawn"}
_REGIONS = {"hue", "da_nang"}


class PackageValidationError(ValueError):
    """A field failed provenance or package-contract validation."""


def _required(value: dict[str, Any], field: str, path: str) -> Any:
    if field not in value or value[field] in (None, ""):
        raise PackageValidationError(f"{path}.{field}: required")
    return value[field]


def _observed_at(value: object, path: str) -> datetime:
    if not isinstance(value, str):
        raise PackageValidationError(f"{path}.observed_at: must be an ISO datetime")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PackageValidationError(
            f"{path}.observed_at: must be an ISO datetime"
        ) from exc


def validate_package(package: dict[str, Any]) -> dict[str, Any]:
    """Validate all references and exact source spans before any write occurs."""
    if not isinstance(package, dict):
        raise PackageValidationError("package: must be an object")
    version = package.get("corpus_version", 1)
    if not isinstance(version, int) or version < 1:
        raise PackageValidationError("corpus_version: must be a positive integer")

    documents = package.get("documents", [])
    passages = package.get("passages", [])
    entities = package.get("entities", [])
    aliases = package.get("aliases", [])
    if package.get("release_status", "published") not in {
        "draft", "published", "retired",
    }:
        raise PackageValidationError("release_status: invalid value")
    for name, rows in (("documents", documents), ("passages", passages),
                       ("entities", entities), ("aliases", aliases)):
        if not isinstance(rows, list):
            raise PackageValidationError(f"{name}: must be an array")

    doc_by_key: dict[str, dict[str, Any]] = {}
    for index, doc in enumerate(documents):
        path = f"documents[{index}]"
        key = str(_required(doc, "key", path))
        if key in doc_by_key:
            raise PackageValidationError(f"{path}.key: duplicate {key}")
        raw_text = _required(doc, "raw_text", path)
        _required(doc, "title", path)
        if _required(doc, "region", path) not in _REGIONS:
            raise PackageValidationError(f"{path}.region: invalid value")
        _required(doc, "source_url", path)
        _observed_at(_required(doc, "observed_at", path), path)
        source_type = _required(doc, "source_type", path)
        tier = _required(doc, "tier", path)
        if source_type not in _SOURCE_TYPES:
            raise PackageValidationError(f"{path}.source_type: invalid value")
        if not isinstance(tier, int) or not 1 <= tier <= 4:
            raise PackageValidationError(f"{path}.tier: must be between 1 and 4")
        if not isinstance(raw_text, str):
            raise PackageValidationError(f"{path}.raw_text: must be a string")
        expected_hash = hashlib.sha256(raw_text.encode()).hexdigest()
        if doc.get("content_hash", expected_hash) != expected_hash:
            raise PackageValidationError(f"{path}.content_hash: does not match raw_text")
        doc_by_key[key] = doc

    passage_by_key: dict[str, dict[str, Any]] = {}
    for index, passage in enumerate(passages):
        path = f"passages[{index}]"
        key = str(_required(passage, "key", path))
        doc_key = str(_required(passage, "document_key", path))
        if key in passage_by_key:
            raise PackageValidationError(f"{path}.key: duplicate {key}")
        if doc_key not in doc_by_key:
            raise PackageValidationError(f"{path}.document_key: unknown reference {doc_key}")
        start, end = passage.get("char_start"), passage.get("char_end")
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
            raise PackageValidationError(f"{path}.char_start/char_end: invalid span")
        expected = doc_by_key[doc_key]["raw_text"][start:end]
        if passage.get("text") != expected:
            raise PackageValidationError(f"{path}.text: does not match document span")
        passage_by_key[key] = passage

    entity_keys: set[str] = set()
    for index, entity in enumerate(entities):
        path = f"entities[{index}]"
        key = str(_required(entity, "key", path))
        if key in entity_keys:
            raise PackageValidationError(f"{path}.key: duplicate {key}")
        if _required(entity, "type", path) not in _ENTITY_TYPES:
            raise PackageValidationError(f"{path}.type: invalid value")
        _required(entity, "name", path)
        if entity.get("entry_status", "published") not in _ENTRY_STATUSES:
            raise PackageValidationError(f"{path}.entry_status: invalid value")
        if not isinstance(entity.get("in_scope", True), bool):
            raise PackageValidationError(f"{path}.in_scope: must be a boolean")
        depth_tier = entity.get("depth_tier", 1)
        if not isinstance(depth_tier, int) or not 1 <= depth_tier <= 3:
            raise PackageValidationError(f"{path}.depth_tier: must be between 1 and 3")
        passage_key = str(_required(entity, "passage_key", path))
        if passage_key not in passage_by_key:
            raise PackageValidationError(f"{path}.passage_key: unknown reference {passage_key}")
        quote = _required(entity, "quote", path)
        if quote not in passage_by_key[passage_key]["text"]:
            raise PackageValidationError(f"{path}.quote: not present in passage")
        entity_keys.add(key)

    for index, alias in enumerate(aliases):
        path = f"aliases[{index}]"
        _required(alias, "alias", path)
        if str(_required(alias, "entity_key", path)) not in entity_keys:
            raise PackageValidationError(f"{path}.entity_key: unknown reference")
        passage_key = str(_required(alias, "passage_key", path))
        if passage_key not in passage_by_key:
            raise PackageValidationError(f"{path}.passage_key: unknown reference")
        if alias.get("alias_type", "common") not in _ALIAS_TYPES:
            raise PackageValidationError(f"{path}.alias_type: invalid value")
        confidence = alias.get("confidence", 1.0)
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise PackageValidationError(f"{path}.confidence: must be between 0 and 1")
        if _required(alias, "quote", path) not in passage_by_key[passage_key]["text"]:
            raise PackageValidationError(f"{path}.quote: not present in passage")
    return package
