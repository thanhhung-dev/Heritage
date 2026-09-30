"""Chat endpoint - main API."""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.rag import retrieve_context
from backend.core.llm import generate_response

log = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    use_rag: bool = True
    history: list[dict] = []


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict] = []
    corrected_from: str = ""
    corrected_to: str = ""
    needs_user_choice: bool = False
    suggestions: list[dict] = []


# Confidence thresholds
CONFIDENCE_HIGH = 0.9   # auto-correct + answer
CONFIDENCE_LOW = 0.7    # below: keep original


def _resolve_correction(
    corrections: list[dict],
) -> tuple[str, str, str, bool, list[dict]]:
    """Xử lý correction theo confidence threshold.

    Trả về (notice, corrected_from, corrected_to, needs_user_choice, suggestions).
    - score >= 0.9: auto-correct, trả lời luôn
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

    # Confidence thấp → giữ nguyên
    return ("", "", "", False, [])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message trống")

    sources: list[dict] = []
    corrections: list[dict] = []
    context = ""

    if req.use_rag:
        try:
            context, sources, corrections = retrieve_context(req.message)
            if not context and req.history:
                last_user_msg = next((m["content"] for m in reversed(req.history) if m.get("role") == "user"), None)
                if last_user_msg:
                    combined_msg = f"{last_user_msg}\n{req.message}"
                    context, sources, corrections = retrieve_context(combined_msg)
        except Exception:
            log.exception("retrieval lỗi, trả lời với context rỗng")
            context, sources, corrections = "", [], []

    notice, corrected_from, corrected_to, needs_user_choice, suggestions = (
        _resolve_correction(corrections)
    )

    # Nếu cần user chọn → trả suggestions, không gọi LLM
    if needs_user_choice:
        return ChatResponse(
            answer="",
            sources=[],
            needs_user_choice=True,
            suggestions=suggestions,
        )

    llm_question = req.message
    if corrected_from and corrected_to:
        llm_question = req.message.replace(corrected_from, corrected_to)
        remaining = req.message.replace(corrected_from, "").strip(" \t\r\n?!.,")
        if not remaining:
            llm_question = f"Hãy giới thiệu về {corrected_to}."

    try:
        if req.history:
            answer = generate_response(
                question=llm_question,
                context=context,
                history=req.history,
            )
        else:
            answer = generate_response(
                question=llm_question,
                context=context,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    return ChatResponse(
        answer=notice + answer,
        sources=sources,
        corrected_from=corrected_from,
        corrected_to=corrected_to,
    )