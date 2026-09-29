"""Validate and atomically import a curated Schema v2 knowledge package."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.textutil import strip_accents
from apps.backend.db.base import AsyncSessionLocal
from apps.backend.models.kg import (
    CorpusRelease, Document, Entity, EntityAlias, EntityAliasEvidence,
    EntityEvidence, Passage,
)

_NS = uuid.UUID("dc6ca935-a876-4b80-9900-9789a2c42386")
_SOURCE_TYPES = {"official", "academic", "management", "press", "encyclopedia", "other"}
_ENTITY_TYPES = {"person", "place", "event", "artifact"}
_ALIAS_TYPES = {"official", "historical", "common", "sino_vietnamese", "english", "typo"}


class PackageValidationError(ValueError):
    """A field failed provenance or package-contract validation."""


def _required(value: dict[str, Any], field: str, path: str) -> Any:
    if field not in value or value[field] in (None, ""):
        raise PackageValidationError(f"{path}.{field}: required")
    return value[field]


def _stable_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(_NS, f"{kind}:{key}")


def _normalize(value: str) -> str:
    return " ".join(strip_accents(value).lower().split())


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
        _required(doc, "region", path)
        _required(doc, "source_url", path)
        _required(doc, "observed_at", path)
        source_type = _required(doc, "source_type", path)
        tier = _required(doc, "tier", path)
        if source_type not in _SOURCE_TYPES:
            raise PackageValidationError(f"{path}.source_type: invalid value")
        if not isinstance(tier, int) or not 1 <= tier <= 4:
            raise PackageValidationError(f"{path}.tier: must be between 1 and 4")
        if not isinstance(raw_text, str):
            raise PackageValidationError(f"{path}.raw_text: must be a string")
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
        passage_key = str(_required(entity, "passage_key", path))
        if passage_key not in passage_by_key:
            raise PackageValidationError(f"{path}.passage_key: unknown reference {passage_key}")
        quote = _required(entity, "quote", path)
        if quote not in passage_by_key[passage_key]["text"]:
            raise PackageValidationError(f"{path}.quote: not present in passage")
        entity_keys.add(key)

    for index, alias in enumerate(aliases):
        path = f"aliases[{index}]"
        if str(_required(alias, "entity_key", path)) not in entity_keys:
            raise PackageValidationError(f"{path}.entity_key: unknown reference")
        passage_key = str(_required(alias, "passage_key", path))
        if passage_key not in passage_by_key:
            raise PackageValidationError(f"{path}.passage_key: unknown reference")
        if alias.get("alias_type", "common") not in _ALIAS_TYPES:
            raise PackageValidationError(f"{path}.alias_type: invalid value")
        if _required(alias, "quote", path) not in passage_by_key[passage_key]["text"]:
            raise PackageValidationError(f"{path}.quote: not present in passage")
    return package


async def import_package(session: AsyncSession, package: dict[str, Any]) -> dict[str, int]:
    """Upsert one validated package in the caller's single transaction."""
    package = validate_package(package)
    version = package.get("corpus_version", 1)
    release_status = package.get("release_status", "published")
    if release_status not in {"draft", "published", "retired"}:
        raise PackageValidationError("release_status: invalid value")
    await session.execute(insert(CorpusRelease).values(
        version=version, status=release_status).on_conflict_do_update(
            index_elements=[CorpusRelease.version], set_={"status": release_status}))

    doc_ids: dict[str, uuid.UUID] = {}
    for doc in package.get("documents", []):
        content_hash = doc.get("content_hash") or hashlib.sha256(doc["raw_text"].encode()).hexdigest()
        doc_id = _stable_id("document", f"{doc['source_url']}:{content_hash}")
        doc_ids[doc["key"]] = doc_id
        values = {"id": doc_id, "title": doc["title"], "region": doc["region"],
                  "source_url": doc["source_url"], "source_type": doc["source_type"],
                  "tier": doc["tier"], "observed_at": doc["observed_at"],
                  "content_hash": content_hash, "raw_text": doc["raw_text"],
                  "license": doc.get("license")}
        await session.execute(insert(Document).values(**values).on_conflict_do_update(
            index_elements=[Document.id], set_={k: v for k, v in values.items() if k != "id"}))

    passage_ids: dict[str, uuid.UUID] = {}
    for passage in package.get("passages", []):
        doc_id = doc_ids[passage["document_key"]]
        passage_id = _stable_id("passage", f"{doc_id}:{version}:{passage['char_start']}")
        passage_ids[passage["key"]] = passage_id
        values = {"id": passage_id, "document_id": doc_id, "text": passage["text"],
                  "char_start": passage["char_start"], "char_end": passage["char_end"],
                  "corpus_version": version}
        await session.execute(insert(Passage).values(**values).on_conflict_do_update(
            index_elements=[Passage.id], set_={"text": passage["text"], "char_end": passage["char_end"]}))

    entity_ids: dict[str, uuid.UUID] = {}
    for entity in package.get("entities", []):
        normalized = _normalize(entity["name"])
        entity_id = _stable_id("entity", f"{entity['type']}:{normalized}")
        entity_ids[entity["key"]] = entity_id
        passage_id = passage_ids[entity["passage_key"]]
        values = {"id": entity_id, "name": entity["name"], "normalized_name": normalized,
                  "type": entity["type"], "in_scope": entity.get("in_scope", True),
                  "depth_tier": entity.get("depth_tier", 1),
                  "entry_status": entity.get("entry_status", "published"),
                  "source_document_id": doc_ids[package["passages"][[p["key"] for p in package["passages"]].index(entity["passage_key"])]["document_key"]],
                  "source_passage_id": passage_id}
        await session.execute(insert(Entity).values(**values).on_conflict_do_update(
            index_elements=[Entity.id], set_={k: v for k, v in values.items() if k != "id"}))
        await session.execute(insert(EntityEvidence).values(entity_id=entity_id, passage_id=passage_id).on_conflict_do_nothing())

    for alias in package.get("aliases", []):
        entity_id = entity_ids[alias["entity_key"]]
        normalized = _normalize(alias["alias"])
        alias_id = _stable_id("alias", f"{entity_id}:{normalized}")
        passage_id = passage_ids[alias["passage_key"]]
        values = {"id": alias_id, "entity_id": entity_id, "alias": alias["alias"],
                  "normalized_alias": normalized, "alias_type": alias.get("alias_type", "common"),
                  "confidence": alias.get("confidence", 1.0), "source_passage_id": passage_id}
        await session.execute(insert(EntityAlias).values(**values).on_conflict_do_update(
            index_elements=[EntityAlias.id], set_={k: v for k, v in values.items() if k != "id"}))
        await session.execute(insert(EntityAliasEvidence).values(
            entity_alias_id=alias_id, passage_id=passage_id).on_conflict_do_nothing())
    return {"documents": len(doc_ids), "passages": len(passage_ids),
            "entities": len(entity_ids), "aliases": len(package.get("aliases", []))}


async def import_file(path: Path) -> dict[str, int]:
    package = json.loads(path.read_text(encoding="utf-8"))
    async with AsyncSessionLocal() as session, session.begin():
        return await import_package(session, package)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nhập knowledge package có provenance")
    parser.add_argument("package", type=Path)
    print(json.dumps(asyncio.run(import_file(parser.parse_args().package))))
