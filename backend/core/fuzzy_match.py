"""Fuzzy matching cho địa danh - suggest correction khi user gõ sai tén.

Tích hợp vào retrieval pipeline: khi find_seeds() trả rỗng, dùng fuzzy match
trên word n-grams để tìm địa danh gần nhất trong knowledge graph thay vì để
REQUIRE_GRAPH_ANCHOR ném sạch kết quả.

Không phụ thuộc extract_names() vì regex đó yêu cầu chữ hoa đầu tên riêng,
mà user thường gõ thường toàn tập ("lăng an định" thay vì "Lăng An Định").
"""
from __future__ import annotations

import difflib
import re
from functools import lru_cache

from backend.core.textutil import strip_accents, WORD_RE, nfc


LOCATION_TYPE_PREFIXES = tuple(
    tuple(prefix.split())
    for prefix in (
        "bao tang", "ban dao", "nha tho", "hoang thanh", "kinh thanh",
        "bien", "cau", "cho", "chua", "cung", "dan", "den", "deo",
        "dinh", "dien", "dong", "ho", "lang", "mieu", "nui", "quan",
        "song", "thanh", "tinh", "xa",
    )
)
QUESTION_BOUNDARY_WORDS = frozenset({
    "a", "dau", "gi", "khong", "nao", "o", "tai", "the", "thuoc", "vay",
})


@lru_cache(maxsize=1)
def _build_name_index(graph) -> tuple[list[str], list[str], list[str]]:
    """Xây index (chuỗi khớp, tên bài chuẩn, chuỗi khớp không dấu)."""
    matched_names: list[str] = []
    canonical_names: list[str] = []
    seen: set[str] = set()
    # Chỉ gợi ý bài có nguồn để sau khi sửa tên luôn có thể trả lời. Alias dùng
    # để khớp nhưng kết quả hiển thị vẫn là tên bài chuẩn.
    for _, data in graph.nodes(data=True):
        if data.get("kind") != "doc":
            continue
        canonical = data["label"]
        for matched in (canonical, *data.get("aliases", ())):
            plain = strip_accents(matched)
            if len(matched) < 4 or plain in seen:
                continue
            seen.add(plain)
            matched_names.append(matched)
            canonical_names.append(canonical)

    stripped = [strip_accents(n) for n in matched_names]
    return matched_names, canonical_names, stripped


def _without_location_type(tokens: list[str]) -> list[str]:
    for prefix in LOCATION_TYPE_PREFIXES:
        if tuple(tokens[:len(prefix)]) == prefix:
            return tokens[len(prefix):]
    return tokens


def _is_single_edit(a: str, b: str) -> bool:
    """True khi hai từ chỉ khác đúng một ký tự thêm, xóa hoặc thay thế."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    shorter, longer = (a, b) if len(a) < len(b) else (b, a)
    for i in range(len(longer)):
        if longer[:i] + longer[i + 1:] == shorter:
            return True
    return False


def _fuzzy_score(a: str, b: str) -> float:
    """Điểm tương đồng 0..1, kết hợp char-level và word-level."""
    char_ratio = difflib.SequenceMatcher(None, a, b).ratio()
    a_tokens, b_tokens = a.split(), b.split()
    a_words, b_words = set(a_tokens), set(b_tokens)
    if a_words and b_words:
        word_overlap = len(a_words & b_words) / max(len(a_words), len(b_words))
    else:
        word_overlap = 0.0
    score = 0.5 * char_ratio + 0.5 * word_overlap

    # Phần tên riêng trùng hoàn toàn và chỉ sai danh từ loại là tín hiệu mạnh,
    # áp dụng chung cả danh từ loại nhiều từ như "bảo tàng" và "nhà thờ".
    a_core = _without_location_type(a_tokens)
    b_core = _without_location_type(b_tokens)
    if (
        len(a_core) >= 2
        and a_core == b_core
        and a_core != a_tokens
        and b_core != b_tokens
    ):
        return 0.96
    if (
        len(a_core) >= 2
        and a_core == b_core
        and (a_core != a_tokens or b_core != b_tokens)
    ):
        return 0.92

    # Một lỗi gõ trong đúng một từ ("Xơn" -> "Sơn") đủ an toàn để tự sửa khi
    # các từ còn lại trùng đúng vị trí. Tên mơ hồ, thiếu từ không được nâng điểm.
    if len(a_tokens) >= 2 and len(a_tokens) == len(b_tokens):
        changed = [(x, y) for x, y in zip(a_tokens, b_tokens) if x != y]
        if len(changed) == 1 and _is_single_edit(*changed[0]):
            return max(score, 0.94)

    return score


def rank_fuzzy_names(
    query: str,
    names: list[str],
    cutoff: float = 0.5,
) -> list[tuple[int, float]]:
    """Xếp hạng name/alias trong database bằng các cụm từ của câu hỏi.

    Index trong kết quả trỏ về phần tử của ``names``. Tên một từ chỉ được dùng
    làm gợi ý mơ hồ, không đủ điểm để tự chọn một entity.
    """
    query_tokens = WORD_RE.findall(strip_accents(query))
    if not query_tokens or not names:
        return []

    normalized_names = [" ".join(WORD_RE.findall(strip_accents(name))) for name in names]
    max_name_words = max((len(name.split()) for name in normalized_names), default=0)
    best_scores: dict[int, float] = {}

    for size in range(1, min(max_name_words, len(query_tokens)) + 1):
        for start in range(len(query_tokens) - size + 1):
            gram_tokens = query_tokens[start:start + size]
            if (
                gram_tokens[0] in QUESTION_BOUNDARY_WORDS
                or gram_tokens[-1] in QUESTION_BOUNDARY_WORDS
            ):
                continue
            gram = " ".join(gram_tokens)
            gram_words = set(gram_tokens)

            for index, candidate in enumerate(normalized_names):
                candidate_words = set(candidate.split())
                if not gram_words & candidate_words:
                    continue
                if size == 1:
                    score = 0.68 if gram in candidate_words and len(gram) >= 4 else 0.0
                else:
                    score = _fuzzy_score(gram, candidate)
                if score >= cutoff and score > best_scores.get(index, 0.0):
                    best_scores[index] = score

    return sorted(best_scores.items(), key=lambda item: (-item[1], item[0]))


def _find_ngram_in_query(query: str, gram_stripped: str) -> tuple[int, int] | None:
    """Tìm vị trí (start, end) của n-gram trong query gốc."""
    q_tokens_raw = WORD_RE.findall(nfc(query).lower())
    q_tokens_stripped = [strip_accents(t) for t in q_tokens_raw]
    gram_tokens = gram_stripped.split()
    n = len(gram_tokens)

    token_spans = [(m.start(), m.end()) for m in WORD_RE.finditer(nfc(query))]
    if len(token_spans) != len(q_tokens_raw):
        return None

    for i in range(len(q_tokens_stripped) - n + 1):
        if q_tokens_stripped[i : i + n] == gram_tokens:
            start = token_spans[i][0]
            end = token_spans[i + n - 1][1]
            return (start, end)
    return None


def suggest_corrections(
    query: str,
    graph,
    max_suggestions: int = 3,
    cutoff: float = 0.5,
) -> list[dict]:
    """Tìm địa danh gần nhất cho tên riêng sai trong câu hỏi.

    Sinh word n-grams từ query rồi fuzzy match với tên địa danh đã bỏ dấu.
    Trả về [{"original": "lăng an định", "suggested": "Cung An Định", "score": 0.82}].
    `original` là chuỗi trong query gốc (có dấu) để replace trực tiếp.
    """
    matched_names, canonical_names, stripped = _build_name_index(graph)
    if not matched_names:
        return []

    q_stripped_tokens = WORD_RE.findall(strip_accents(query))
    max_name_words = max(len(name.split()) for name in stripped)

    candidates: list[tuple[float, int, str]] = []
    seen: set[tuple[str, str]] = set()

    for size in range(2, min(max_name_words, len(q_stripped_tokens)) + 1):
        for i in range(len(q_stripped_tokens) - size + 1):
            gram_tokens = q_stripped_tokens[i : i + size]
            if (
                gram_tokens[0] in QUESTION_BOUNDARY_WORDS
                or gram_tokens[-1] in QUESTION_BOUNDARY_WORDS
            ):
                continue
            gram = " ".join(gram_tokens)
            gram_words = set(gram.split())

            for idx, cand_stripped in enumerate(stripped):
                if not gram_words & set(cand_stripped.split()):
                    continue
                score = _fuzzy_score(gram, cand_stripped)
                if score >= cutoff:
                    key = (gram, canonical_names[idx])
                    if key not in seen:
                        seen.add(key)
                        candidates.append((score, idx, gram))

    candidates.sort(reverse=True, key=lambda x: x[0])
    results: list[dict] = []
    used_suggested: set[str] = set()
    for score, idx, gram in candidates:
        suggested = canonical_names[idx]
        if suggested in used_suggested:
            continue
        used_suggested.add(suggested)
        # Tìm vị trí trong query gốc để replace
        span = _find_ngram_in_query(query, gram)
        if span:
            original = query[span[0] : span[1]]
        else:
            original = gram
        results.append({
            "original": original,
            "suggested": suggested,
            "score": round(score, 2),
        })
        if len(results) >= max_suggestions:
            break

    return results
