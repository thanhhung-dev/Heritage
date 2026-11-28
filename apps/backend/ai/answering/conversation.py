"""Conversational grounded QA: history resolves intent, passages supply evidence."""
from __future__ import annotations

import re
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.backend.ai.answering.prompt import user_msg
from apps.backend.services.heritage_graph import in_entity_follow_up, neighbor_follow_ups
from apps.backend.services.tour_scope import area_system_policy, allowed_output, normalized, resolve_area

_SOCIAL = frozenset({"hi", "hello", "xin chao", "chao", "cam on", "ban la ai"})


def is_social_turn(question: str) -> bool:
    return normalized(question) in _SOCIAL

_DIALOGUE_QUESTION = re.compile(
    r"(?:^| )(?:nay h|nai |luc nay|vua noi|vua hoi|vua tra loi|nhac lai|lap lai|"
    r"toi noi gi|ban noi gi|minh noi gi|noi gi ay|tra loi gi|cau tra loi)(?: |$)"
)


def is_dialogue_question(question: str) -> bool:
    """True only when the user asks what was just said in this chat."""
    return bool(_DIALOGUE_QUESTION.search(f" {normalized(question)} "))


_SOURCE_LABEL = re.compile(
    r"\[\s*(?:tư liệu|tu lieu|passage)?\s*(?:id\s*[:：])?\s*(?:PSG-)?[A-Za-z0-9_-]{6,}\s*\]"
    r"|\[\s*\d+\s*\]"
    r"|\b(?:tư liệu|tu lieu|passage)\s+id\s*[:：]\s*PSG-[a-fA-F0-9]+\b"
    r"|\bPSG-[a-fA-F0-9]{16,}\b",
    re.I,
)


def visible_answer(text: str) -> str:
    """Drop source labels. Citations belong in sources, not in the spoken answer."""
    cleaned = _SOURCE_LABEL.sub("", text or "")
    cleaned = re.sub(r"\b[Pp]assage\b", "", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"([,.;:]){2,}", r"\1", cleaned)
    return cleaned.strip(" \t,;")


REWRITE_SYSTEM = """Bạn viết lại câu hỏi cuối thành một câu tiếng Việt đủ nghĩa để tìm tài liệu.
Chỉ dùng các câu hỏi trước của người dùng để nối đối tượng hoặc thuộc tính còn thiếu.
Không lấy dữ kiện từ trí nhớ. Không trả lời kiến thức.
Nếu câu cuối đã đủ nghĩa, kể cả khi đổi chủ đề, chép nguyên câu đó.
Chỉ in đúng một câu hỏi, không giải thích, không JSON.
/no_think"""


def prior_user_questions(history: list[dict] | None) -> list[str]:
    return [
        item["content"].strip()
        for item in (history or [])
        if item.get("role") == "user" and isinstance(item.get("content"), str) and item["content"].strip()
    ][-6:]


def dialogue_turns(history: list[dict] | list[str] | None) -> list[dict[str, str]]:
    """Bounded user/assistant turns. Strings are prior user questions."""
    turns: list[dict[str, str]] = []
    for item in history or []:
        if isinstance(item, str):
            role, content = "user", item
        elif isinstance(item, dict):
            role, content = item.get("role"), item.get("content")
        else:
            continue
        if role not in {"user", "assistant"} or not isinstance(content, str) or not content.strip():
            continue
        turns.append({"role": role, "content": content.strip()[:2000]})
    turns = turns[-6:]
    while turns and sum(len(item["content"]) for item in turns) > 6000:
        turns.pop(0)
    while turns and turns[0]["role"] == "assistant":
        turns.pop(0)
    return turns


def rewrite_messages(question: str, prior: list[str]) -> list[dict[str, str]]:
    lines = []
    if prior:
        lines.append("Câu hỏi trước:")
        lines.extend(f"- {text}" for text in prior)
        lines.append("")
    lines.append(f"Câu hỏi cuối: {question.strip()}")
    return [
        {"role": "system", "content": REWRITE_SYSTEM},
        {"role": "user", "content": "\n".join(lines)},
    ]


def standalone_question(raw: str, original: str) -> str:
    text = (raw or "").strip().splitlines()[0].strip().strip("`\"'")
    if not text or text.startswith("{") or len(text) > 2000:
        return original
    return text


def rewrite_followup(question: str, history: list[dict] | None, generate) -> str:
    prior = prior_user_questions(history)
    if not prior:
        return question
    try:
        return standalone_question(
            generate(question=question, rewrite=True, user_history=prior),
            question,
        )
    except Exception:
        return question


def _normalize_source_id(raw_id: str) -> str:
    cleaned = raw_id.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1].strip()
    if cleaned.lower().startswith("passage "):
        cleaned = cleaned[8:].strip()
    return cleaned


def resolve_cited_source_ids(cited_ids: list[str], valid_ids: set[str]) -> list[str]:
    """Match normalized source IDs against supplied evidence IDs (including missing PSG- prefix)."""
    resolved: list[str] = []
    for raw_id in cited_ids:
        sid = _normalize_source_id(raw_id)
        if sid not in valid_ids and f"PSG-{sid}" in valid_ids:
            sid = f"PSG-{sid}"
        resolved.append(sid)
    return list(dict.fromkeys(resolved))


def evidence_cite_id(item) -> str:
    """URL trong dataset nếu có; không thì id passage."""
    url = getattr(item, "source_url", None) or ""
    return str(url).strip() or str(item.id)


def grounded_source_ids(cited_ids: list[str], valid_ids: set[str]) -> list[str]:
    return [sid for sid in resolve_cited_source_ids(cited_ids, valid_ids) if sid in valid_ids]


def conversation_json_schema(context: str = "") -> dict:
    """JSON outcome with scoped answer type, citations and optional follow-up questions."""
    passage_ids = list(dict.fromkeys(re.findall(r"^\[Passage ([^\]]+)\]", context, flags=re.MULTILINE)))
    items: dict = {"type": "string", "enum": passage_ids} if passage_ids else {"type": "string"}
    source_ids = {
        "type": "array",
        "items": items,
        "maxItems": len(passage_ids) if passage_ids else 0,
    }
    return {
        "type": "object",
        "properties": {
            "answer_type": {
                "type": "string",
                "enum": ["answered", "conversation", "insufficient_evidence", "out_of_scope"],
            },
            "answer": {"type": "string", "minLength": 1},
            "source_ids": source_ids,
            "follow_up_questions": {
                "type": "array",
                "items": {"type": "string", "minLength": 1, "maxLength": 200},
                "maxItems": 3,
            },
        },
        "required": ["answer_type", "answer", "source_ids"],
        "additionalProperties": False,
    }


class ConversationAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    answer_type: Literal["answered", "conversation", "insufficient_evidence", "out_of_scope"]
    answer: str = Field(min_length=1)
    source_ids: list[str]
    follow_up_questions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        self.source_ids = [_normalize_source_id(sid) for sid in self.source_ids]
        if self.answer_type != "answered" and self.source_ids:
            raise ValueError("non-factual outcomes cannot cite evidence")
        return self


def graph_follow_up_topics(graph_context: list[dict] | None) -> list[str]:
    topics: list[str] = []
    for item in graph_context or []:
        if not isinstance(item, dict):
            continue
        source, target = item.get("source"), item.get("target")
        title = item.get("title") or item.get("name")
        if isinstance(source, str) and isinstance(target, str) and source.strip() and target.strip():
            label = f"{source.strip()} — {target.strip()}"
        elif isinstance(title, str) and title.strip():
            label = title.strip()
        else:
            continue
        if label not in topics:
            topics.append(label)
        if len(topics) == 8:
            break
    return topics


def append_graph_follow_up_hint(context: str, graph_context: list[dict] | None) -> str:
    topics = graph_follow_up_topics(graph_context)
    if not topics:
        return context
    hint = "Chủ đề GraphRAG cho câu hỏi tiếp (không cần cite): " + "; ".join(topics)
    if len(context) + len(hint) + 2 > 4800:
        return context
    return f"{context}\n\n{hint}"


def clean_follow_ups(values: list[str], asked: str) -> list[str]:
    asked_norm = normalized(asked)
    accepted: list[str] = []
    for raw in values:
        question = " ".join(raw.split())
        if (not question or len(question) > 200 or question in accepted
                or normalized(question) == asked_norm or not allowed_output(question)):
            continue
        accepted.append(question)
        if len(accepted) == 3:
            break
    return accepted


_FOLLOW_UP_PATTERNS = (
    "{topic} có ý nghĩa hoặc vai trò gì?",
    "{topic} gắn với nhân vật hay sự kiện nào?",
    "Kiến trúc hoặc hiện vật nào liên quan tới {topic}?",
)


def related_follow_ups(
    values: list[str], asked: str, *, graph_context: list[dict] | None = None,
    evidence=(), area_title: str | None = None, focus_title: str | None = None,
) -> list[str]:
    """Start with the current entity, then related entities and GraphRAG topics."""
    first = in_entity_follow_up(asked, area_title=area_title, focus_title=focus_title)
    accepted = clean_follow_ups(
        ([first] if first else []) + neighbor_follow_ups(asked, area_title=area_title) + list(values), asked,
    )
    if len(accepted) >= 2:
        return accepted[:3]
    asked_norm = normalized(asked)
    seeds = graph_follow_up_topics(graph_context)
    for item in evidence or ():
        note = " ".join(str(getattr(item, "location_note", "") or "").split())
        if note and len(note) <= 80 and note not in seeds:
            seeds.append(note)
    if area_title and area_title not in seeds:
        seeds.append(area_title)
    for topic in seeds:
        label = topic.split(" — ", 1)[0].strip() or topic
        for pattern in _FOLLOW_UP_PATTERNS:
            candidate = pattern.format(topic=label)
            if (normalized(candidate) == asked_norm or candidate in accepted
                    or not allowed_output(candidate)):
                continue
            accepted.append(candidate)
            if len(accepted) == 3:
                return accepted
    return accepted





CONVERSATION_SYSTEM = """Bạn là trợ lý AI HeritageGraph, hỗ trợ khám phá di sản,
lịch sử và văn hóa Việt Nam, tập trung vào Đà Nẵng và Huế.

CĂN CỨ
- Chỉ kể điều Passage nói. Thiếu thì nói thiếu, không bịa năm, danh hiệu,
  địa chỉ, sự kiện hay quan hệ.
- Nguồn không nhắc một chi tiết không chứng minh chi tiết đó không có.
- Hội thoại đã gửi không phải bằng chứng lịch sử. Chỉ khi người dùng xin nhắc lại
  vừa nói hoặc vừa trả lời gì thì answer_type=conversation, source_ids=[],
  chỉ dựa trên các lượt đó. Không có lượt trước thì nói chưa có. Câu hỏi về
  lịch sử, nhân vật, sự kiện hoặc kiến trúc của địa điểm đang xem không phải conversation.
- Passage chỉ dùng khi câu hỏi hỏi địa điểm hoặc cổ vật đang xem.
  Có Passage không có nghĩa là phải answered. Không chép câu trả lời trước
  cho một câu hỏi mới.

CÁCH TRẢ LỜI
- Tiếng Việt tự nhiên, giọng của bạn. Trả lời đúng câu họ hỏi trước.
  Câu xác nhận hoặc đính chính thì xác nhận/đính chính ngắn gọn nếu nguồn đủ căn cứ;
  không kể lại toàn bộ phần giới thiệu. Câu hỏi mới được ưu tiên hơn chủ đề cũ.
  Không mặc định đồng ý với giả định trong câu hỏi; đối chiếu Passage trước.
- Không URL, id, chữ Passage hay nhãn Tư liệu id trong answer. Id chỉ nằm trong source_ids.
- Ngoài phạm vi: nhận câu họ vừa hỏi, nói mình chỉ có biết chỗ này,
  rồi mời hỏi tiếp về chỗ này. Tự viết, không dùng câu mẫu, không đọc Passage, không bịa số.

ĐẦU RA
Trả duy nhất JSON với answer_type, answer và source_ids. Không Markdown.
Nhãn [Passage id] chỉ để điền source_ids. Không viết nhãn đó, id, chữ Passage
hay Tư liệu id vào answer.
- answered: câu hỏi về địa điểm hoặc cổ vật đang xem, và Passage trả lời được
  ít nhất một phần của điều đang hỏi. Điền id vào source_ids. Chỉ nói phần còn thiếu
  khi câu hỏi thực sự yêu cầu chi tiết đó; không thêm lời thiếu tư liệu cho câu xác nhận đã đủ căn cứ.
- conversation: xã giao hoặc câu hỏi về hội thoại này; source_ids=[].
insufficient_evidence: câu hỏi đúng địa điểm hoặc cổ vật đang xem, nhưng nguồn
  là (không có) hoặc các Passage không chứa thông tin trả lời được câu hỏi này;
  source_ids=[]. Nói rõ chưa có tư liệu về chi tiết này, không gượng ép kể dữ kiện
  lạc đề từ Passage.
- out_of_scope: chủ đề khác (giá, tin tức, thời tiết, việc không thuộc di sản)
  hoặc địa điểm khác, kể cả khi nguồn vẫn có Passage của khu đang xem.
  source_ids=[]. Không kể dữ kiện Passage.
/no_think"""


def conversation_messages(
    source: str, question: str, retrieval_status: str = "available",
    *, active_area_id: str | None = None, user_history: list[str] | None = None,
    dialogue: list[dict] | None = None, artifact_title: str | None = None,
    viewing_context: str | None = None,
) -> list[dict[str, str]]:
    system = CONVERSATION_SYSTEM
    if active_area_id:
        system += area_system_policy(resolve_area(active_area_id), artifact_title=artifact_title)
    if viewing_context:
        system += (
            "\nNgữ cảnh giao diện đã được máy chủ xác thực (chỉ định vị đối tượng, không thay thế Passage): "
            + viewing_context
        )
    body = user_msg(source, question)
    turns = dialogue_turns(dialogue if dialogue is not None else user_history)
    if turns:
        instruction = (
            "Câu này hỏi về hội thoại bên trên. Chỉ dùng các lượt đó, không dùng Passage."
            if is_dialogue_question(question) else
            "Hội thoại trước chỉ để nối mạch và xác định đối tượng, không phải bằng chứng lịch sử. "
            "Trả lời câu hỏi hiện tại từ Passage; câu hỏi xác nhận cần xác nhận hoặc đính chính trực tiếp."
        )
        body = instruction + "\n\n" + body
    if retrieval_status != "available":
        body = f"retrieval_status: {retrieval_status}\n\n{body}"
    return [
        {"role": "system", "content": system},
        *turns,
        {"role": "user", "content": body},
    ]
