"""Chat endpoint - main API.

Pipeline (migration guide §5.1):
  1. DB entity resolution (new) — nếu có entity + location verified → trả template
  2. Fuzzy match correction (existing)
  3. BM25 + graph retrieval (existing)
  4. LLM generation (existing)

DB lookup là lớp trước, pipeline cũ vẫn là fallback khi DB không có dữ liệu.
"""
import logging
import re

from fastapi import APIRouter, Depends, HTTPException

from pydantic import BaseModel

from backend.core.fuzzy_match import LOCATION_TYPE_PREFIXES, _without_location_type
from backend.core.rag import retrieve_context
from backend.core.llm import generate_response
from backend.core.textutil import strip_accents, WORD_RE
from backend.db.base import AsyncSessionLocal
from backend.services.kg import KgRepository, EntityCandidate
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    use_rag: bool = True
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict] = []
    corrected_from: str = ""
    corrected_to: str = ""
    needs_user_choice: bool = False
    suggestions: list[dict] = []
    entity_id: str | None = None
    intent: str | None = None
    resolution_status: str | None = None
    answer_type: str | None = None


CONFIDENCE_HIGH = 0.9
CONFIDENCE_LOW = 0.7

_LOCATION_INTENT_RE = re.compile(
    r"(ở đâu|ở chỗ nào|ở đâu ạ|ở đâu vậy|ở đâu không|"
    r"địa chỉ|nằm ở|ở phường|ở quận|ở tỉnh|"
    r"tọa lạc|vị trí|bao xa)",
    re.IGNORECASE,
)


def _detect_intent(message: str) -> str | None:
    """Detect 'location' intent từ query (migration guide §5.2)."""
    if _LOCATION_INTENT_RE.search(message):
        return "location"
    return None


def _intro_question_for_bare_entity(message: str, sources: list[dict]) -> str:
    """Biến một tên entity đứng riêng thành câu hỏi, tránh model hiểu là NER."""
    if not sources or not sources[0].get("doc"):
        return message

    canonical = sources[0]["doc"]
    query_tokens = WORD_RE.findall(strip_accents(message))
    canonical_tokens = WORD_RE.findall(strip_accents(canonical))
    query_core = _without_location_type(query_tokens)
    canonical_core = _without_location_type(canonical_tokens)
    is_canonical_name = query_core == canonical_core
    is_unambiguous_prefix = (
        len(query_core) >= 2
        and canonical_core[:len(query_core)] == query_core
    )
    if is_canonical_name or is_unambiguous_prefix:
        return f"Hãy giới thiệu tổng quan và những nét đặc biệt của {canonical}."
    return message


def _resolve_correction(
    corrections: list[dict],
) -> tuple[str, str, str, bool, list[dict]]:
    """Xử lý correction theo confidence threshold.

    Trả về (notice, corrected_from, corrected_to, needs_user_choice, suggestions).
    - score >= 0.9: auto-correct, trả lời luời
    - 0.7 <= score < 0.9: để user chọn
    - score < 0.7: giữ nguyên query gốc
    """
    if not corrections:
        return ("", "", "", False, [])

    top = corrections[0]
    candidates = [
        c for c in corrections
        if c["score"] >= CONFIDENCE_LOW
        and c["score"] >= top["score"] - 0.15
    ]
    unique: list[dict] = []
    seen = set()
    for candidate in candidates:
        if candidate["suggested"] not in seen:
            seen.add(candidate["suggested"])
            unique.append(candidate)

    if top["score"] >= CONFIDENCE_HIGH or len(unique) == 1:
        notice = (
            f'Nếu bạn muốn nói **{top["suggested"]}** '
            f'(không phải **{top["original"]}**) thì:\n\n'
        )
        return (notice, top["original"], top["suggested"], False, [])

    if unique:
        return ("", "", "", True, unique[:3])

    return ("", "", "", False, [])


async def _try_db_location_answer(
    db: AsyncSession, message: str,
) -> ChatResponse | None:
    """DB-based entity resolution layer (migration guide §5.2).

    Trả về ChatResponse cho mọi location intent. Chỉ intent khác mới fallback.
    KHÔNG đưa location intent xuống LLM khi database thiếu dữ liệu hoặc bị lỗi.
    """
    intent = _detect_intent(message)
    if not intent:
        return None

    try:
        repo = KgRepository(db)
        candidates = await repo.resolve_entities(
            message, limit=5,
        )
    except Exception:
        log.exception("DB entity resolution lỗi")
        return ChatResponse(
            answer=(
                "Tôi chưa thể kiểm tra dữ liệu địa điểm trong database, nên không "
                "thể trả lời vị trí một cách có bằng chứng."
            ),
            intent=intent,
            resolution_status="unavailable",
            answer_type="insufficient_evidence",
        )

    if not candidates:
        return ChatResponse(
            answer=(
                "Tôi không tìm thấy địa danh này trong database đã xác minh, nên "
                "chưa thể trả lời vị trí hoặc cung cấp nguồn đáng tin cậy."
            ),
            intent=intent,
            resolution_status="not_found",
            answer_type="insufficient_evidence",
        )

    # Migration guide §5.3: nhiều ứng viên → suggestions, không gọi LLM
    if len(candidates) > 1:
        return ChatResponse(
            answer="",
            needs_user_choice=True,
            suggestions=[c.to_dict() for c in candidates[:3]],
            intent=intent,
            resolution_status="ambiguous",
            answer_type="suggestion",
        )

    # Đủ 1 candidate → lấy verified location
    cand: EntityCandidate = candidates[0]
    try:
        locations = await repo.get_verified_locations(cand.entity.id)
    except Exception:
        log.exception("get_verified_locations lỗi")
        return ChatResponse(
            answer=(
                f"Tôi đã nhận diện được {cand.entity.name}, nhưng chưa thể kiểm tra "
                "địa chỉ đã xác minh trong database."
            ),
            entity_id=str(cand.entity.id),
            intent=intent,
            resolution_status="unavailable",
            answer_type="insufficient_evidence",
        )

    if not locations:
        return ChatResponse(
            answer=(
                f"Tôi đã nhận diện được {cand.entity.name}, nhưng database chưa có "
                "địa chỉ đã được xác minh kèm nguồn. Tôi chưa thể trả lời vị trí "
                "để tránh cung cấp thông tin không có bằng chứng."
            ),
            entity_id=str(cand.entity.id),
            intent=intent,
            resolution_status="resolved",
            answer_type="insufficient_evidence",
        )

    if len(locations) > 1:
        return ChatResponse(
            answer=(
                f"Database đang có nhiều địa chỉ đã xác minh cho {cand.entity.name} "
                "nhưng chưa đủ thông tin để xác định bản ghi đang có hiệu lực. "
                "Dữ liệu cần được rà soát trước khi trả lời."
            ),
            entity_id=str(cand.entity.id),
            intent=intent,
            resolution_status="ambiguous",
            answer_type="insufficient_evidence",
        )

    loc = locations[0]
    # Migration guide §5.4: template trả lời địa chỉ
    parts: list[str] = [loc.address]  # address luôn có (NOT NULL)
    for part in (loc.ward, loc.district, loc.province):
        if part and not any(part.casefold() in existing.casefold() for existing in parts):
            parts.append(part)

    answer = f"{cand.entity.name} nằm tại {', '.join(parts)}."

    return ChatResponse(
        answer=answer,
        sources=[
            {
                "passage_id": str(cand.entity.id),
                "doc": loc.source_title or "",
                "url": loc.source_url,
                "quote": loc.source_sentence[:200] if loc.source_sentence else "",
            }
        ],
        entity_id=str(cand.entity.id),
        intent=intent,
        resolution_status="resolved",
        answer_type="db_location",
    )


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message trống")

    # --- DB entity resolution (migration guide §5.1-5.2) ---
    db_response = await _try_db_location_answer(db, req.message)
    if db_response is not None:
        return db_response

    # --- Existing pipeline: fuzzy match + BM25/graph + LLM (fallback) ---
    sources: list[dict] = []
    corrections: list[dict] = []
    context = ""
    effective_message = req.message

    if req.use_rag:
        try:
            context, sources, corrections = retrieve_context(req.message)
        except Exception:
            log.exception("retrieval lỗi, trả lời với context rỗng")
            context, sources, corrections = "", [], []

        intro_question = _intro_question_for_bare_entity(req.message, sources)
        if intro_question != req.message:
            effective_message = intro_question
            try:
                intro_context, intro_sources, intro_corrections = retrieve_context(
                    effective_message
                )
                if intro_context.strip() and intro_sources:
                    context = intro_context
                    sources = intro_sources
                    corrections = intro_corrections
            except Exception:
                log.exception("retrieval lại cho tên entity đứng riêng bị lỗi")

        # Khi retrieval thất bại, thử resolve entity từ DB (bao gồm address-based)
        # rồi dùng canonical name để rerun retrieval. Ví dụ:
        # "kể chi tiết về nhà thờ trần phú" → resolve → "Nhà thờ chính tòa Đà Nẵng"
        if not context.strip() or not sources:
            try:
                from backend.services.kg import KgRepository
                repo = KgRepository(db)
                resolved = await repo.resolve_entities(req.message, limit=3)

                if len(resolved) == 1:
                    # Single match → dùng canonical name để rerun retrieval
                    canonical = resolved[0].entity.name
                    # Thay phần tên entity trong query bằng canonical name.
                    # Tìm type prefix (nhà thờ, chùa, lăng...) trong query,
                    # rồi replace type prefix + tên sai → canonical name,
                    # giữ lại prefix và suffix.
                    q_stripped = strip_accents(req.message).lower()
                    tokens = WORD_RE.findall(q_stripped)
                    token_spans = [
                        (m.start(), m.end())
                        for m in WORD_RE.finditer(strip_accents(req.message))
                    ]

                    # Tìm type prefix trong tokens
                    replaced = False
                    for prefix_tokens in sorted(
                        LOCATION_TYPE_PREFIXES, key=len, reverse=True
                    ):
                        n = len(prefix_tokens)
                        for i in range(len(tokens) - n + 1):
                            if tuple(tokens[i:i + n]) == prefix_tokens:
                                if i < len(token_spans):
                                    # Vị trí bắt đầu type prefix
                                    entity_start = token_spans[i][0]
                                    # Ước tính entity name end: type prefix tokens
                                    # + core keywords (tên riêng)
                                    end_idx = i + n
                                    # Skip qua tên riêng: tokens cho đến khi
                                    # gặp từ >= 4 chars không phải tên riêng
                                    # hoặc hết query
                                    for j in range(i + n, len(tokens)):
                                        # Giữ lại tokens ngắn hoặc đã biết
                                        # là phần tên riêng
                                        if tokens[j] in {
                                            "co", "gi", "dac", "biet", "o",
                                            "dau", "la", "the", "nao",
                                        }:
                                            end_idx = j
                                            break
                                        end_idx = j + 1

                                    text_prefix = req.message[:entity_start]
                                    if end_idx < len(token_spans):
                                        text_suffix = " " + req.message[
                                            token_spans[end_idx][0]:
                                        ]
                                    else:
                                        text_suffix = ""
                                    effective_message = (
                                        text_prefix + canonical + text_suffix
                                    )
                                    replaced = True
                                    break
                        if replaced:
                            break

                    if not replaced:
                        effective_message = f"Hãy kể chi tiết về {canonical}"

                    log.info(
                        "Entity resolved via DB, rerun retrieval: %s → %s",
                        req.message, effective_message,
                    )
                    try:
                        context, sources, corrections = retrieve_context(effective_message)
                        if context.strip() and sources:
                            corrections = []  # Clear corrections vì đã resolve đúng
                    except Exception:
                        log.exception("rerun retrieval lỗi")

                elif len(resolved) > 1:
                    # Multiple matches → trả suggestions
                    return ChatResponse(
                        answer="",
                        needs_user_choice=True,
                        suggestions=[c.to_dict() for c in resolved[:3]],
                        resolution_status="ambiguous",
                        answer_type="suggestion",
                    )
            except Exception:
                log.exception("DB entity resolution fallback lỗi")

    notice, corrected_from, corrected_to, needs_user_choice, suggestions = (
        _resolve_correction(corrections)
    )

    if needs_user_choice:
        return ChatResponse(
            answer="",
            sources=[],
            needs_user_choice=True,
            suggestions=suggestions,
        )

    if not context.strip() or not sources:
        return ChatResponse(
            answer=(
                "Tôi không tìm thấy nguồn phù hợp trong dữ liệu hiện có, nên chưa "
                "thể trả lời câu hỏi này mà không suy đoán."
            ),
            sources=[],
            answer_type="insufficient_evidence",
        )

    llm_question = effective_message
    if corrected_from and corrected_to:
        llm_question = effective_message.replace(corrected_from, corrected_to)
        remaining = effective_message.replace(corrected_from, "").strip(" \t\r\n?!.,")
        if not remaining:
            llm_question = f"Hãy giới thiệu về {corrected_to}."

    try:
        answer = generate_response(
            question=llm_question,
            context=context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    return ChatResponse(
        answer=notice + answer,
        sources=sources,
        corrected_from=corrected_from,
        corrected_to=corrected_to,
    )
