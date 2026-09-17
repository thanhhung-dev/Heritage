"""Core RAG module - GraphRAG retrieval (hybrid lexical + knowledge graph).

Trả về context ĐÚNG HÌNH DẠNG mà LoRA được train: một đoạn văn liền mạch, vì
mỗi mẫu train có `Nguồn:` là nội dung của MỘT chunk. Nối nhiều chunk bằng dấu
phân cách lạ là tạo ra định dạng model chưa từng thấy.

Khi không tìm được đoạn đủ liên quan thì trả về context RỖNG - `llm.py` sẽ ghi
"Nguồn: (không có)", đúng dạng các mẫu refusal đã train, nên model từ chối lịch
sự thay vì bịa. Đây là hành vi mong muốn, không phải lỗi.
"""
from __future__ import annotations

from backend.core.retriever import get_retriever, is_admin_chunk, is_lead
REQUIRE_GRAPH_ANCHOR = True
MIN_COVERAGE = 0.25  

MIN_COVERAGE_OVER_HITS = True
REQUIRE_EVIDENCE_FOR_NAMED = True

REQUIRE_SUBJECT_EVIDENCE = True
REQUIRE_KNOWN_ADMIN = True

CONTEXT_MAX_CHARS = 2200
MAX_CONTEXT_CHUNKS = 2

SECOND_DOC_RATIO = 0.75

SNIPPET_CHARS = 240


def _snippet(text: str) -> str:
    if len(text) <= SNIPPET_CHARS:
        return text
    cut = text.rfind(" ", 0, SNIPPET_CHARS)
    return text[: cut if cut > 0 else SNIPPET_CHARS].rstrip(" ,;:") + " ..."


def _ensure_lead(picked: list[dict], hits: list[dict], top_doc: str) -> list[dict]:
    """Ép đoạn MỞ ĐẦU của bài tốt nhất có mặt trong context.

    Câu kiểm chứng vị trí ("Chùa Thiên Mụ ở Đà Nẵng đúng không") chỉ bác được khi
    nguồn có tỉnh/thành, và ở corpus wiki đoạn mở đầu gần như LUÔN có nó. Không
    có nó thì model không có gì để phản biện: nó lách bằng cách nói vòng
    ("một địa điểm nổi tiếng ở Đàng Trong") - tức là bịa.

    Đổi CHỖ chứ không thêm chỗ: vẫn đúng MAX_CONTEXT_CHUNKS, không làm context
    dài hơn mẫu train.
    """
    if any(is_lead(p) for p in picked):
        return picked
    lead = next((h for h in hits if h["doc_node"] == top_doc and is_lead(h)), None)
    if lead is None:
        return picked
    if len(picked) < MAX_CONTEXT_CHUNKS:
        return picked + [lead]
    return picked[:-1] + [lead]


def _ensure_ward(picked: list[dict], hits: list[dict], top_doc: str) -> list[dict]:
    """Ép chunk có NÊU ĐƠN VỊ HÀNH CHÍNH của bài tốt nhất vào context.

    Với câu hỏi cấp phường, đoạn mở đầu KHÔNG đủ: bài Thành Điện Hải mở đầu bằng
    "tọa lạc tại thành phố Đà Nẵng", còn "phường Thạch Thang" nằm ở chunk #1 và #7.
    `_ensure_lead` ép đúng cái chunk không chứa câu trả lời, nên câu "Thành Điện
    Hải thuộc phường nào" nhận nguồn nói về tỉnh - model hoặc bịa tên phường hoặc
    trả lời lệch câu hỏi.

    Đổi CHỖ chứ không thêm chỗ, như `_ensure_lead`.
    """
    if any(is_admin_chunk(p) for p in picked):
        return picked
    ward = next((h for h in hits if h["doc_node"] == top_doc and is_admin_chunk(h)), None)
    if ward is None:
        return picked
    if len(picked) < MAX_CONTEXT_CHUNKS:
        return picked + [ward]
    return picked[:-1] + [ward]


def retrieve_context(query: str, top_k: int = 3) -> tuple[str, list[dict], list[dict]]:
    """Trả về (context_text, list_of_source_dicts, corrections).

    Source dict: {text, score, doc, heading, url, chunk_id, graph, graph_hits}
    Corrections: [{"original": "lăng an định", "suggested": "Cung An Định", "score": 0.82}]
    """
    res = get_retriever().retrieve(query, top_k=top_k)
    hits = res["hits"]
    corrections = res.get("corrections", [])
    if not hits:
        return ("", [], corrections)
    if REQUIRE_GRAPH_ANCHOR and not res["anchored"]:
        return ("", [], corrections)
    if REQUIRE_KNOWN_ADMIN and res["foreign_admin"]:
        return ("", [], corrections)
    best_coverage = (max(h["coverage"] for h in hits) if MIN_COVERAGE_OVER_HITS
                     else hits[0]["coverage"])
    if best_coverage < MIN_COVERAGE:
        return ("", [], corrections)
    if REQUIRE_EVIDENCE_FOR_NAMED and res["specific"]:
        top = hits[0]
        if not top["named"] and not top["graph_hits"]:
            return ("", [], corrections)
    if REQUIRE_SUBJECT_EVIDENCE and res["subject"]:
        subject = res["subject"]
        if not any(h["doc"] == subject or subject in h["graph_hits"] for h in hits[:1]):
            return ("", [], corrections)

    top_doc, top_score = hits[0]["doc"], hits[0]["score"]
    picked: list[dict] = []
    total = 0
    for h in hits:
        if h["doc"] != top_doc and h["score"] < SECOND_DOC_RATIO * top_score:
            continue
        if total + len(h["text"]) > CONTEXT_MAX_CHARS and picked:
            break
        picked.append(h)
        total += len(h["text"])
        if len(picked) >= MAX_CONTEXT_CHUNKS:
            break

    if "location" in res["intent"] or "general" in res["intent"]:
        picked = _ensure_lead(picked, hits, hits[0]["doc_node"])
    if "ward" in res["intent"]:
        picked = _ensure_ward(picked, hits, hits[0]["doc_node"])

    picked.sort(key=lambda h: (h["doc"] != top_doc, h["chunk_id"]))
    context = " ".join(h["text"] for h in picked)

    sources = [
        {
            "text": _snippet(h["text"]),
            "score": h["score"],
            "doc": h["doc"],
            "heading": h["heading"],
            "url": h["url"],
            "chunk_id": h["chunk_id"],
            "graph": h["graph"],
            "graph_hits": h["graph_hits"],
            "used_in_context": any(p["chunk_id"] == h["chunk_id"] for p in picked),
        }
        for h in hits
    ]
    return (context, sources, corrections)
