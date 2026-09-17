"""Repository/service layer cho Knowledge Graph — entity resolution + location lookup.

Migration guide §5.3 đề xuất repository API:
  - resolve_entities(query, region) -> EntityCandidate
  - get_verified_locations(entity_id, at) -> PlaceLocation
  - get_entity_evidence(entity_id) -> Evidence

Quy tắc: repository chỉ truy vấn dữ liệu. Confidence, intent, câu trả lời ở service layer.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.fuzzy_match import rank_fuzzy_names, _without_location_type, QUESTION_BOUNDARY_WORDS
from backend.core.textutil import strip_accents, WORD_RE, STOPWORDS
from backend.models.kg import Entity, EntityAlias, PlaceLocation, Passage, Document


# Từ chỉ vùng hành chính quá chung — không dùng làm keyword match address.
# (single tokens vì WORD_RE tách từng từ: "da nang" → ["da", "nang"])
_REGION_STOPWORDS = frozenset({
    "hue", "da", "nang", "hoa", "noi", "gon", "hcm",
    "mien", "trung", "bac",
})

# Từ phân loại địa chỉ — không mang thông tin tên riêng.
_ADDRESS_CLASSIFIERS = frozenset({
    "duong", "pho", "quan", "phuong", "tinh", "huyen", "xa", "thon",
    "so", "hem", "ngo", "ngach",
})


def _extract_core_keywords(query: str) -> list[str]:
    """Tách phần tên riêng/đường phố còn lại sau khi bỏ type prefix + stopwords.

    Ví dụ: "nhà thờ trần phú đà nẵng" → ["tran", "phu"]
    (bỏ "nha tho" = type prefix, bỏ "da", "nang" = region stopword)

    Dùng cho address-based entity resolution khi name/alias không match.
    """
    q_stripped = strip_accents(query).lower().strip()
    tokens = WORD_RE.findall(q_stripped)
    if not tokens:
        return []

    # Bỏ location type prefix ("nha tho", "chua", "lang"...)
    core = _without_location_type(tokens)
    if not core:
        core = tokens

    # Bỏ stopwords + question words + region names + address classifiers
    skip = STOPWORDS | QUESTION_BOUNDARY_WORDS | _REGION_STOPWORDS | _ADDRESS_CLASSIFIERS
    result = [t for t in core if t not in skip and len(t) >= 2]
    return result


class EntityCandidate:
    """Kết quả ứng viên từ entity resolver — chưa phải quyết định cuối cùng."""
    __slots__ = ("entity", "alias", "score", "sources")

    def __init__(self, entity: Entity, alias: EntityAlias | None = None,
                 score: float = 1.0, sources: list[dict] | None = None):
        self.entity = entity
        self.alias = alias
        self.score = score
        self.sources = sources or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": str(self.entity.id),
            "canonical_name": self.entity.name,
            "normalized_name": self.entity.normalized_name,
            "type": self.entity.type,
            "alias_used": self.alias.alias if self.alias else None,
            "score": round(self.score, 3),
            "sources": self.sources,
        }


class KgRepository:
    """Repository chỉ truy vấn — không chứa intent detection hay confidence threshold."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_entities(
        self, query: str, region: str | None = None,
        limit: int = 10,
    ) -> list[EntityCandidate]:
        """Tìm entity khớp với query qua name + alias.

        Áp dụng ranking theo migration guide §1.3:
          1. Tên chuẩn khớp chính xác.
          2. Alias đã xác minh.
          3. Khu vực xuất hiện trong câu hỏi.
          5. Confidence và số nguồn hỗ trợ.

        Query có thể chứa từ định hướng ("ở đâu", "địa chỉ") — dùng POSITION
        substring match thay vì exact equality để handle điều này.
        """
        q_norm = strip_accents(query).lower().strip()
        if not q_norm:
            return []

        # Minimum length để tránh false positive với tên ngắn ("an", "định")
        MIN_NAME_LEN = 4

        candidates: list[EntityCandidate] = []

        # Priority 1: exact normalized_name match
        rows = await self.db.execute(
            select(Entity).where(
                text("LENGTH(normalized_name) >= :min_len AND LOWER(:q) = LOWER(normalized_name)"),
            ).params(q=q_norm, min_len=MIN_NAME_LEN).limit(limit)
        )
        for e in rows.scalars():
            candidates.append(EntityCandidate(e, score=1.0))

        # Priority 2: substring match (alias appears trong query)
        if len(candidates) < limit:
            alias_rows = await self.db.execute(
                select(EntityAlias, Entity)
                .join(Entity, EntityAlias.entity_id == Entity.id)
                .where(
                    text("LENGTH(normalized_alias) >= :min_len AND POSITION(LOWER(normalized_alias) IN LOWER(:q)) > 0"),
                )
                .params(q=q_norm, min_len=MIN_NAME_LEN)
                .limit(limit - len(candidates))
            )
            for alias, entity in alias_rows:
                candidates.append(EntityCandidate(
                    entity, alias=alias,
                    score=min(float(alias.confidence), 1.0) if alias.confidence else 0.8,
                    sources=[{"document_id": str(alias.source_document_id)}] if alias.source_document_id else [],
                ))

        # Priority 3: substring match (entity name appears trong query, chưa có ở trên)
        if len(candidates) < limit:
            name_rows = await self.db.execute(
                select(Entity).where(
                    text("LENGTH(normalized_name) >= :min_len AND POSITION(LOWER(normalized_name) IN LOWER(:q)) > 0"),
                ).params(q=q_norm, min_len=MIN_NAME_LEN).limit(limit - len(candidates))
            )
            seen_ids = {c.entity.id for c in candidates}
            for e in name_rows.scalars():
                if e.id not in seen_ids:
                    candidates.append(EntityCandidate(e, score=0.9))

        # Priority 4: address-based resolution — user nhớ tên đường/phường thay vì
        # tên chính thức. Ví dụ "nhà thờ trần phú đà nẵng" → entity có address
        # chứa "Trần Phú". Chỉ chạy khi name/alias match đều rỗng.
        if not candidates:
            core_keywords = _extract_core_keywords(query)
            if len(core_keywords) >= 2:
                # Lấy tất cả place_location kèm entity (type=place)
                loc_rows = await self.db.execute(
                    select(PlaceLocation, Entity)
                    .join(Entity, PlaceLocation.entity_id == Entity.id)
                    .where(Entity.type == "place")
                )

                addr_candidates: dict[uuid.UUID, tuple[Entity, float]] = {}
                for loc, entity in loc_rows:
                    # Tokenize từng field riêng để check co-location
                    address_words = set(WORD_RE.findall(
                        strip_accents(loc.address or "").lower()
                    ))
                    ward_words = set(WORD_RE.findall(
                        strip_accents(loc.ward or "").lower()
                    ))
                    district_words = set(WORD_RE.findall(
                        strip_accents(loc.district or "").lower()
                    ))
                    
                    # Count matches in each field
                    addr_matched = sum(1 for kw in core_keywords if kw in address_words)
                    ward_matched = sum(1 for kw in core_keywords if kw in ward_words)
                    district_matched = sum(1 for kw in core_keywords if kw in district_words)
                    
                    # Total unique matched keywords
                    all_matched_keywords = set()
                    for kw in core_keywords:
                        if kw in address_words or kw in ward_words or kw in district_words:
                            all_matched_keywords.add(kw)
                    
                    total_matched = len(all_matched_keywords)
                    if total_matched == 0:
                        continue

                    ratio = total_matched / len(core_keywords)
                    
                    # Bonus khi keywords cùng xuất hiện trong address field
                    # (thay vì rải ra address + ward + district)
                    co_location_bonus = 0.0
                    if addr_matched >= 2 and addr_matched == total_matched:
                        co_location_bonus = 0.15  # Tất cả keywords trong address
                    elif addr_matched >= 2:
                        co_location_bonus = 0.10  # Nhiều keywords trong address
                    
                    # Cần ít nhất 50% keywords match, và ít nhất 1 keyword dài
                    # (>= 4 chars) để tránh false positive với từ ngắn ("an", "ly")
                    all_words = address_words | ward_words | district_words
                    has_long_match = any(
                        kw in all_words for kw in core_keywords if len(kw) >= 4
                    )
                    
                    if ratio >= 0.5 and has_long_match:
                        # Boost nếu location đã verified
                        base_score = 0.70 * ratio + co_location_bonus
                        if loc.verification_status == "verified":
                            base_score = min(base_score + 0.10, 0.95)

                        existing = addr_candidates.get(entity.id)
                        if existing is None or base_score > existing[1]:
                            addr_candidates[entity.id] = (entity, base_score)

                for entity, score in sorted(
                    addr_candidates.values(), key=lambda x: -x[1]
                ):
                    candidates.append(EntityCandidate(entity, score=score))
                    if len(candidates) >= limit:
                        break

        # Fallback: fuzzy match trên toàn bộ tên địa điểm và alias đã import.
        # Chỉ chạy khi exact/substring/address đều rỗng để không làm yếu tín hiệu chắc chắn.
        if not candidates:
            fuzzy_rows = await self.db.execute(
                select(Entity, EntityAlias)
                .outerjoin(EntityAlias, EntityAlias.entity_id == Entity.id)
                .where(Entity.type == "place")
            )
            names: list[str] = []
            records: list[tuple[Entity, EntityAlias | None]] = []
            for entity, alias in fuzzy_rows:
                names.append(alias.alias if alias else entity.name)
                records.append((entity, alias))
                if alias is not None:
                    names.append(entity.name)
                    records.append((entity, None))

            ranked = rank_fuzzy_names(query, names)
            best_by_entity: dict[uuid.UUID, EntityCandidate] = {}
            for index, score in ranked:
                entity, alias = records[index]
                current = best_by_entity.get(entity.id)
                if current is None or score > current.score:
                    best_by_entity[entity.id] = EntityCandidate(
                        entity,
                        alias=alias,
                        score=score,
                        sources=(
                            [{"document_id": str(alias.source_document_id)}]
                            if alias and alias.source_document_id else []
                        ),
                    )

            fuzzy_candidates = sorted(best_by_entity.values(), key=lambda c: -c.score)
            if fuzzy_candidates:
                top_score = fuzzy_candidates[0].score
                if top_score >= 0.72:
                    close = [c for c in fuzzy_candidates if c.score >= top_score - 0.08]
                    candidates = close[:limit]
                elif top_score >= 0.68:
                    # Một từ chung (ví dụ "thanh") chỉ đủ để đưa suggestions.
                    candidates = [c for c in fuzzy_candidates if c.score == top_score][:limit]

        # Nhiều alias của cùng một địa điểm có thể đồng thời xuất hiện trong câu.
        # Chúng vẫn chỉ là một entity, không phải tình huống mơ hồ.
        unique_candidates: dict[uuid.UUID, EntityCandidate] = {}
        for candidate in candidates:
            current = unique_candidates.get(candidate.entity.id)
            if current is None or candidate.score > current.score:
                unique_candidates[candidate.entity.id] = candidate
        candidates = list(unique_candidates.values())

        # Filter by region if specified
        if region:
            region_lower = region.lower()
            region_filtered = [
                c for c in candidates
                if c.entity.normalized_name
                and region_lower in strip_accents(c.entity.normalized_name).lower()
            ]
            if region_filtered:
                candidates = region_filtered

        return sorted(candidates, key=lambda c: -c.score)

    async def get_verified_locations(
        self, entity_id: uuid.UUID, at: date | None = None,
    ) -> list[PlaceLocation]:
        """Lấy location có status=verified, lọc theo thời gian nếu `at` được chỉ định.

        Không dùng valid_to IS NULL như quyết định duy nhất — migration guide §5.3:
        valid_to NULL không tức là hiện hành. Phải có valid_from <= at.
        """
        stmt = (
            select(PlaceLocation)
            .where(
                PlaceLocation.entity_id == entity_id,
                PlaceLocation.verification_status == "verified",
            )
            .order_by(PlaceLocation.created_at.desc())
        )
        if at is not None:
            stmt = stmt.where(
                PlaceLocation.valid_from <= at,
                PlaceLocation.valid_to.is_(None) | (PlaceLocation.valid_to >= at),
            )

        rows = await self.db.execute(stmt)
        return list(rows.scalars().all())

    async def get_entity_evidence(
        self, entity_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Lấy citation/quote từ passage gắn với entity qua document.

        Entity.source_document_id -> Document.id -> Passage.document_id
        Migration guide §5.7: quote phải nằm trong passage, không sinh nguồn giả.
        """
        stmt = (
            select(
                Document.title.label("source_title"),
                Document.source_url.label("source_url"),
            )
            .join(Passage, Passage.document_id == Document.id)
            .join(Entity, Entity.source_document_id == Document.id)
            .where(Entity.id == entity_id)
            .order_by(Document.created_at.desc())
            .limit(5)
        )
        rows = await self.db.execute(stmt)
        return [dict(row._mapping) for row in rows]
