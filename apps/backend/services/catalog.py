"""Bounded published catalog reads; no model inference or document loading."""
from urllib.parse import unquote, urlsplit

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import and_, exists, or_, select

from apps.backend.core.assets import asset_policy
from apps.backend.models.heritage import Heritage
from apps.backend.models.heritage_classification import CulturalContent, HeritageCategory, HeritageClassification
from apps.backend.models.model_asset import ModelAsset
from apps.backend.models.scene import Scene
from apps.backend.schemas.catalog import ArtifactFacts, CatalogCard, VerifiedFact, safe_url

SECTION_KEYS = ("featured", "artifacts_treasures", "people_traditions", "festivals_practices", "artifact_collection")


def public_conditions():
    return (CulturalContent.publish_state == "published", CulturalContent.classification_status == "applied",
            CulturalContent.classified_revision == CulturalContent.input_revision,
            CulturalContent.entity_type.is_not(None),
            or_(CulturalContent.source_heritage_id.is_(None), exists(select(Heritage.id).where(
                Heritage.id == CulturalContent.source_heritage_id, Heritage.publish_state == "published").correlate(CulturalContent))))


def primary_in(keys):
    return exists(select(HeritageClassification.content_id).where(
        HeritageClassification.content_id == CulturalContent.id,
        HeritageClassification.is_primary.is_(True), HeritageClassification.category_key.in_(keys)))


def section_condition(section):
    kind = CulturalContent.entity_type
    if section == "artifact_collection":
        return kind == "artifact"
    if section == "artifacts_treasures":
        return kind == "collection"
    if section == "festivals_practices":
        return or_(kind == "event", and_(kind == "practice", primary_in(["ritual", "festival"])))
    if section == "people_traditions":
        return or_(kind == "person", and_(kind == "practice", primary_in(
            ["community_tradition", "traditional_craft", "intangible_heritage"])))
    if section == "featured":
        tour = exists(select(Scene.id).join(ModelAsset, ModelAsset.scene_id == Scene.id).where(
            Scene.heritage_id == CulturalContent.source_heritage_id, ModelAsset.file_url != ""))
        return and_(CulturalContent.is_featured.is_(True), or_(and_(kind == "place", tour),
                    and_(kind == "practice", primary_in(["cultural_experience"]))))
    raise HTTPException(422, "Unknown homepage section.")


def image_url(raw):
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
        if (raw != raw.strip() or any(ord(c) < 32 for c in raw) or "\\" in raw or raw.startswith("//")
                or parsed.scheme not in {"", "http", "https"} or parsed.username or parsed.password
                or (parsed.scheme and not parsed.hostname)
                or parsed.fragment or any(part == ".." for part in unquote(parsed.path).split("/"))):
            return None
        resolved = asset_policy().resolve(raw)
        if resolved and not urlsplit(resolved).scheme:
            return "/" + resolved.lstrip("/")
        return resolved
    except ValueError:
        return None


def verified_facts(raw):
    facts = {}
    for key in ArtifactFacts.model_fields:
        try:
            if isinstance(raw, dict) and raw.get(key) is not None:
                facts[key] = VerifiedFact.model_validate(raw[key])
        except ValidationError:
            continue  # Never expose an unverified free-text field as a fact.
    return ArtifactFacts(**facts)


class CatalogService:
    def __init__(self, db):
        self.db = db

    async def categories(self):
        return (await self.db.scalars(select(HeritageCategory).order_by(HeritageCategory.key))).all()

    async def cards(self, rows, *, require_image=False):
        ids = [row[0].id for row in rows]
        classifications = (await self.db.scalars(select(HeritageClassification).where(
            HeritageClassification.content_id.in_(ids)).order_by(HeritageClassification.category_key))).all() if ids else []
        grouped = {}
        for classification in classifications:
            grouped.setdefault(classification.content_id, []).append(classification)
        result = []
        for content, heritage_slug in rows:
            keys = grouped.get(content.id, [])
            primary = next((row.category_key for row in keys if row.is_primary), None)
            if primary is None:
                continue
            source = content.source_url
            try:
                if source:
                    safe_url(source)
            except ValueError:
                source = None
            if content.source_heritage_id is None and (not source or not content.entity_type_hint):
                continue
            image = image_url(content.card_image_url) or image_url(content.splash_image_url)
            if require_image and not image:
                continue
            href = (f"/content/{heritage_slug}" if content.entity_type == "place" and heritage_slug
                    else f"/catalog/{content.slug}")
            result.append(CatalogCard(id=content.id, slug=content.slug, title=content.title,
                description=content.description, region=content.region, entity_type=content.entity_type,
                categories=[row.category_key for row in keys], primary_category=primary, card_image_url=image,
                source_url=source, metadata=verified_facts(content.verified_metadata),
                heritage_id=content.source_heritage_id, heritage_slug=heritage_slug, href=href))
        return result

    async def page(self, *, category=None, entity_type=None, section=None, sort="title", limit=8, offset=0):
        stmt = select(CulturalContent, Heritage.slug).outerjoin(Heritage, Heritage.id == CulturalContent.source_heritage_id)
        stmt = stmt.where(*public_conditions())
        if category:
            stmt = stmt.where(exists(select(HeritageClassification.content_id).where(
                HeritageClassification.content_id == CulturalContent.id, HeritageClassification.category_key == category)))
        if entity_type:
            stmt = stmt.where(CulturalContent.entity_type == entity_type)
        if section:
            stmt = stmt.where(section_condition(section))
        order = ([CulturalContent.featured_rank] if section == "featured" else [])
        order += [CulturalContent.created_at.desc()] if sort == "newest" else [CulturalContent.title]
        rows = (await self.db.execute(stmt.order_by(*order, CulturalContent.id).offset(offset).limit(limit + 1))).all()
        return {"items": await self.cards(rows[:limit], require_image=bool(section)),
                "next_offset": offset + limit if len(rows) > limit else None}

    async def detail(self, slug):
        rows = (await self.db.execute(select(CulturalContent, Heritage.slug).outerjoin(
            Heritage, Heritage.id == CulturalContent.source_heritage_id).where(
            CulturalContent.slug == slug, *public_conditions()))).all()
        cards = await self.cards(rows)
        if not cards:
            raise HTTPException(404, "Published catalog content not found.")
        from apps.backend.models.heritage_classification import ContentRelation
        relations = (await self.db.execute(select(ContentRelation, CulturalContent, Heritage.slug)
            .join(CulturalContent, CulturalContent.id == ContentRelation.object_id)
            .outerjoin(Heritage, Heritage.id == CulturalContent.source_heritage_id)
            .where(ContentRelation.subject_id == cards[0].id, *public_conditions())
            .order_by(ContentRelation.object_id).limit(100))).all()
        related_cards = await self.cards([(row[1], row[2]) for row in relations])
        related = {card.id: card for card in related_cards}
        return {**cards[0].model_dump(), "related_entities": [{"relation_type": relation.relation_type,
            "content": related[content.id].model_dump(), "source_url": relation.source_url}
            for relation, content, _ in relations if content.id in related]}
