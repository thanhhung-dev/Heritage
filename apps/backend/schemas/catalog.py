"""Public catalog DTOs and strict editorial inputs."""
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, StrictBool, TypeAdapter, field_validator, model_validator

from apps.backend.services.heritage_taxonomy import validate_categories

EntityType = Literal["place", "artifact", "collection", "event", "person", "practice"]
SectionKey = Literal["featured", "artifacts_treasures", "people_traditions", "festivals_practices", "artifact_collection"]
_http_url = TypeAdapter(AnyHttpUrl)


def safe_url(value):
    _http_url.validate_python(value)
    parsed = urlsplit(value)
    if (any(ord(c) < 32 for c in value) or parsed.scheme not in {"http", "https"}
            or not parsed.hostname or parsed.username or parsed.password or parsed.fragment):
        raise ValueError("Supply an HTTP(S) source URL without credentials or fragments")
    return value


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class VerifiedFact(StrictInput):
    value: str = Field(min_length=1, max_length=500)
    source_url: str = Field(max_length=2048)
    _source = field_validator("source_url")(safe_url)


class ArtifactFacts(StrictInput):
    period: VerifiedFact | None = None
    material: VerifiedFact | None = None
    origin: VerifiedFact | None = None
    custodian: VerifiedFact | None = None


class CatalogCard(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None
    region: str | None
    entity_type: EntityType
    categories: list[str]
    primary_category: str
    card_image_url: str | None
    source_url: str | None
    metadata: ArtifactFacts
    heritage_id: int | None
    heritage_slug: str | None
    href: str


class CatalogPage(BaseModel):
    items: list[CatalogCard]
    next_offset: int | None


class RelatedContent(BaseModel):
    relation_type: str
    content: CatalogCard
    source_url: str


class CatalogDetail(CatalogCard):
    related_entities: list[RelatedContent]


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key: str
    name_vi: str
    name_en: str
    description: str | None
    parent_key: str | None


class ClassificationOverride(StrictInput):
    expected_revision: int = Field(gt=0, strict=True)
    entity_type: EntityType
    categories: list[str] = Field(min_length=1, max_length=14)
    primary_category: str
    reasoning_summary: str = Field(min_length=10, max_length=2000)
    locked: StrictBool = True

    @model_validator(mode="after")
    def valid_categories(self):
        validate_categories(self.entity_type, self.categories, self.primary_category)
        return self


class ContentCreate(StrictInput):
    slug: str = Field(min_length=1, max_length=200, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1, max_length=250)
    description: str | None = Field(default=None, max_length=20000)
    tagline: str | None = Field(default=None, max_length=500)
    headline: str | None = Field(default=None, max_length=500)
    region: str | None = Field(default=None, max_length=250)
    entity_type_hint: Literal["artifact", "collection", "event", "person", "practice"]
    source_url: str = Field(max_length=2048)
    card_image_url: str | None = Field(default=None, max_length=2048)
    splash_image_url: str | None = Field(default=None, max_length=2048)
    publish_state: Literal["draft", "published"] = "draft"
    verified_metadata: ArtifactFacts = Field(default_factory=ArtifactFacts)
    knowledge_entity_id: UUID | None = None
    source_document_id: UUID | None = None
    interactive_highlight_id: int | None = Field(default=None, gt=0, lt=2**63, strict=True)
    _source = field_validator("source_url")(safe_url)

    @field_validator("slug")
    @classmethod
    def reserved_slug(cls, value):
        if value.startswith("heritage-"):
            raise ValueError("heritage- is reserved for existing source projections")
        return value


class ContentPatch(StrictInput):
    expected_revision: int = Field(gt=0, strict=True)
    title: str | None = Field(default=None, min_length=1, max_length=250)
    description: str | None = Field(default=None, max_length=20000)
    card_image_url: str | None = Field(default=None, max_length=2048)
    splash_image_url: str | None = Field(default=None, max_length=2048)
    publish_state: Literal["draft", "published"] | None = None
    verified_metadata: ArtifactFacts | None = None
    source_url: str | None = Field(default=None, max_length=2048)
    entity_type_hint: Literal["artifact", "collection", "event", "person", "practice"] | None = None
    is_featured: StrictBool | None = None
    featured_rank: int | None = Field(default=None, ge=0, le=100000, strict=True)

    @model_validator(mode="after")
    def valid_patch(self):
        changed = self.model_fields_set - {"expected_revision"}
        if not changed:
            raise ValueError("Supply a content/editorial change")
        for name in changed & {"title", "publish_state", "verified_metadata", "source_url", "entity_type_hint", "is_featured", "featured_rank"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        if "source_url" in changed:
            safe_url(self.source_url)
        return self


class RelationCreate(StrictInput):
    object_id: int = Field(gt=0, strict=True)
    relation_type: Literal["located_at", "held_at", "associated_with", "member_of", "depicts"]
    source_url: str = Field(max_length=2048)
    _source = field_validator("source_url")(safe_url)
