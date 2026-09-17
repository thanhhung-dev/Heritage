"""Idempotently import the local heritage corpus into PostgreSQL."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.core.corpus import load_docs
from backend.core.textutil import strip_accents


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALIAS_FILE = PROJECT_ROOT / "corpus" / "aliases.json"
VERIFIED_LOCATION_FILE = PROJECT_ROOT / "corpus" / "verified_locations.json"
CORPUS_VERSION = 1
WIKIPEDIA_LICENSE = "CC BY-SA 4.0"

REGION_CODES = {"Huế": "hue", "Đà Nẵng": "da_nang"}
PLACE_CATEGORIES = {"Danh thắng", "Di tích lịch sử", "Làng nghề"}


@dataclass(frozen=True)
class ImportPlan:
    documents: list[dict[str, Any]]
    passages: list[dict[str, Any]]
    entities: list[dict[str, Any]]
    aliases: list[dict[str, Any]]
    locations: list[dict[str, Any]]
    skipped: list[tuple[str, str]]


def _stable_uuid(kind: str, *parts: object) -> uuid.UUID:
    value = ":".join([kind, *(str(part) for part in parts)])
    return uuid.uuid5(uuid.NAMESPACE_URL, value)


def _normalize(value: str) -> str:
    return " ".join(strip_accents(value).split())


def _entity_type(category: str) -> str:
    if category in PLACE_CATEGORIES:
        return "place"
    if category == "Lễ hội":
        return "event"
    return "artifact"


def build_import_plan() -> ImportPlan:
    """Build deterministic rows without connecting to PostgreSQL."""
    corpus_docs, skipped = load_docs()
    aliases_by_name = json.loads(ALIAS_FILE.read_text("utf-8"))
    verified_locations = json.loads(VERIFIED_LOCATION_FILE.read_text("utf-8"))
    location_by_entity = {
        _normalize(item["entity_name"]): item for item in verified_locations
    }

    documents: list[dict[str, Any]] = []
    passages: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    aliases: list[dict[str, Any]] = []
    locations: list[dict[str, Any]] = []

    for doc in corpus_docs:
        region = REGION_CODES[doc["region"]]
        document_id = _stable_uuid("document", doc["url"])
        raw_text = "\n\n".join(chunk["text"] for chunk in doc["chunks"])
        documents.append(
            {
                "id": document_id,
                "title": doc["name"],
                "region": region,
                "source_url": doc["url"],
                "raw_text": raw_text,
                "license": WIKIPEDIA_LICENSE,
            }
        )

        document_passages: list[dict[str, Any]] = []
        char_start = 0
        for chunk in doc["chunks"]:
            text = chunk["text"]
            passage = {
                "id": _stable_uuid(
                    "passage", document_id, CORPUS_VERSION, char_start, text
                ),
                "document_id": document_id,
                "text": text,
                "char_start": char_start,
                "char_end": char_start + len(text),
                "corpus_version": CORPUS_VERSION,
            }
            passages.append(passage)
            document_passages.append(passage)
            char_start = passage["char_end"] + 2

        normalized_name = _normalize(doc["name"])
        entity_type = _entity_type(doc["category"])
        entity_id = _stable_uuid("entity", entity_type, normalized_name)
        source_passage_id = document_passages[0]["id"]
        entities.append(
            {
                "id": entity_id,
                "name": doc["name"],
                "normalized_name": normalized_name,
                "type": entity_type,
                "summary": document_passages[0]["text"][:500],
                "source_document_id": document_id,
                "source_passage_id": source_passage_id,
            }
        )

        raw_aliases = [
            {
                "alias": alias,
                "alias_type": "common",
                "confidence": 1.0,
            }
            for alias in aliases_by_name.get(doc["name"], [])
        ]
        location = location_by_entity.get(normalized_name)
        if location:
            raw_aliases.extend(location.get("query_aliases", []))

        seen_aliases: set[str] = set()
        for alias_data in raw_aliases:
            normalized_alias = _normalize(alias_data["alias"])
            if normalized_alias in seen_aliases:
                continue
            seen_aliases.add(normalized_alias)
            aliases.append(
                {
                    "id": _stable_uuid("alias", entity_id, normalized_alias),
                    "entity_normalized_name": normalized_name,
                    "alias": alias_data["alias"],
                    "normalized_alias": normalized_alias,
                    "alias_type": alias_data.get("alias_type", "common"),
                    "confidence": alias_data.get("confidence", 1.0),
                    "source_document_id": document_id,
                    "source_passage_id": source_passage_id,
                }
            )

    known_entities = {entity["normalized_name"] for entity in entities}
    for item in verified_locations:
        normalized_name = _normalize(item["entity_name"])
        if normalized_name not in known_entities:
            raise ValueError(
                f"Verified location references unknown entity: {item['entity_name']}"
            )
        locations.append(
            {
                **{key: value for key, value in item.items() if key != "query_aliases"},
                "id": _stable_uuid("location", normalized_name, item["source_url"]),
                "entity_normalized_name": normalized_name,
                "verified_at": datetime.fromisoformat(item["verified_at"]),
            }
        )

    return ImportPlan(documents, passages, entities, aliases, locations, skipped)


def _connect(database_url: str):
    import psycopg
    from sqlalchemy.engine import make_url

    url = make_url(database_url)
    return psycopg.connect(
        dbname=url.database,
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
    )


def import_plan(plan: ImportPlan, database_url: str) -> None:
    """Upsert a plan in one transaction and preserve unrelated database rows."""
    with _connect(database_url) as connection:
        with connection.cursor() as cursor:
            for document in plan.documents:
                cursor.execute(
                    """
                    INSERT INTO document
                        (id, title, region, source_url, raw_text, license)
                    VALUES (%(id)s, %(title)s, %(region)s, %(source_url)s,
                            %(raw_text)s, %(license)s)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        region = EXCLUDED.region,
                        source_url = EXCLUDED.source_url,
                        raw_text = EXCLUDED.raw_text,
                        license = EXCLUDED.license,
                        updated_at = now()
                    """,
                    document,
                )

            for passage in plan.passages:
                cursor.execute(
                    """
                    INSERT INTO passage
                        (id, document_id, text, char_start, char_end, corpus_version)
                    VALUES (%(id)s, %(document_id)s, %(text)s, %(char_start)s,
                            %(char_end)s, %(corpus_version)s)
                    ON CONFLICT (id) DO UPDATE SET
                        text = EXCLUDED.text,
                        char_start = EXCLUDED.char_start,
                        char_end = EXCLUDED.char_end
                    """,
                    passage,
                )

            entity_ids: dict[str, uuid.UUID] = {}
            for entity in plan.entities:
                cursor.execute(
                    """
                    SELECT id FROM entity
                    WHERE normalized_name = %s AND type = %s
                    """,
                    (entity["normalized_name"], entity["type"]),
                )
                existing = cursor.fetchone()
                entity_id = existing[0] if existing else entity["id"]
                entity_ids[entity["normalized_name"]] = entity_id
                cursor.execute(
                    """
                    INSERT INTO entity
                        (id, name, normalized_name, type, summary,
                         source_document_id, source_passage_id)
                    VALUES (%(id)s, %(name)s, %(normalized_name)s, %(type)s,
                            %(summary)s, %(source_document_id)s,
                            %(source_passage_id)s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        summary = EXCLUDED.summary,
                        source_document_id = EXCLUDED.source_document_id,
                        source_passage_id = EXCLUDED.source_passage_id,
                        updated_at = now()
                    """,
                    entity | {"id": entity_id},
                )

            for alias in plan.aliases:
                entity_id = entity_ids[alias["entity_normalized_name"]]
                cursor.execute(
                    """
                    SELECT id, entity_id FROM entity_alias
                    WHERE normalized_alias = %s
                    """,
                    (alias["normalized_alias"],),
                )
                existing = cursor.fetchone()
                if existing and existing[1] != entity_id:
                    print(
                        f"Skipping conflicting alias {alias['alias']!r}; "
                        f"already belongs to entity {existing[1]}"
                    )
                    continue
                alias_id = existing[0] if existing else alias["id"]
                cursor.execute(
                    """
                    INSERT INTO entity_alias
                        (id, entity_id, alias, normalized_alias, alias_type,
                         confidence, source_document_id, source_passage_id)
                    VALUES (%(id)s, %(entity_id)s, %(alias)s,
                            %(normalized_alias)s, %(alias_type)s, %(confidence)s,
                            %(source_document_id)s, %(source_passage_id)s)
                    ON CONFLICT (id) DO UPDATE SET
                        alias = EXCLUDED.alias,
                        alias_type = EXCLUDED.alias_type,
                        confidence = EXCLUDED.confidence,
                        source_document_id = EXCLUDED.source_document_id,
                        source_passage_id = EXCLUDED.source_passage_id
                    """,
                    alias | {"id": alias_id, "entity_id": entity_id},
                )

            for location in plan.locations:
                entity_id = entity_ids[location["entity_normalized_name"]]
                cursor.execute(
                    """
                    INSERT INTO place_location
                        (id, entity_id, address, ward, district, province,
                         latitude, longitude, valid_from, valid_to, source_url,
                         source_title, source_sentence, verification_status,
                         verified_at)
                    VALUES
                        (%(id)s, %(entity_id)s, %(address)s, %(ward)s,
                         %(district)s, %(province)s, %(latitude)s, %(longitude)s,
                         %(valid_from)s, %(valid_to)s, %(source_url)s,
                         %(source_title)s, %(source_sentence)s,
                         %(verification_status)s, %(verified_at)s)
                    ON CONFLICT (id) DO UPDATE SET
                        entity_id = EXCLUDED.entity_id,
                        address = EXCLUDED.address,
                        ward = EXCLUDED.ward,
                        district = EXCLUDED.district,
                        province = EXCLUDED.province,
                        latitude = EXCLUDED.latitude,
                        longitude = EXCLUDED.longitude,
                        valid_from = EXCLUDED.valid_from,
                        valid_to = EXCLUDED.valid_to,
                        source_url = EXCLUDED.source_url,
                        source_title = EXCLUDED.source_title,
                        source_sentence = EXCLUDED.source_sentence,
                        verification_status = EXCLUDED.verification_status,
                        verified_at = EXCLUDED.verified_at
                    """,
                    {
                        "ward": None,
                        "district": None,
                        "latitude": None,
                        "longitude": None,
                        "valid_from": None,
                        "valid_to": None,
                        **location,
                        "entity_id": entity_id,
                    },
                )


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    plan = build_import_plan()
    import_plan(plan, database_url)
    print(
        "Imported "
        f"{len(plan.documents)} documents, {len(plan.passages)} passages, "
        f"{len(plan.entities)} entities, {len(plan.aliases)} aliases and "
        f"{len(plan.locations)} verified locations; skipped {len(plan.skipped)} docs"
    )


if __name__ == "__main__":
    main()
