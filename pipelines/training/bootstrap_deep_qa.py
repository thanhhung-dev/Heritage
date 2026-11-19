#!/usr/bin/env python3
"""Sinh train.jsonl / valid.jsonl khớp chatbot hội thoại.

Contract giống serve: CONVERSATION_SYSTEM, Nguồn: [Passage <url trong dataset>],
assistant JSON {answer, source_ids, follow_up_questions}. source_ids là link
tài liệu (locations_index.url), không phải id passage nội bộ.

  python pipelines/training/bootstrap_deep_qa.py
  python pipelines/training/bootstrap_deep_qa.py --use-model
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.backend.ai.answering.conversation import CONVERSATION_SYSTEM  # noqa: E402
from apps.backend.core.corpus import (  # noqa: E402
    INDEX_FILE,
    chunk_document,
    clean_wiki_text,
    is_usable,
    load_docs,
    wiki_url,
)
from apps.backend.core.kg import extract_names  # noqa: E402
from apps.backend.core.prompt import NER_QUESTION, NER_TYPES, SYSTEM, user_msg  # noqa: E402
from apps.backend.core.textutil import contains_name, sentences, strip_accents  # noqa: E402

OUT_TRAIN = ROOT / "data" / "train.jsonl"
OUT_VALID = ROOT / "data" / "valid.jsonl"
DEFAULT_PACKAGE = ROOT / "data" / "ingestion" / "corpus-v202611111011" / "package.json"

SEED = 42
MIN_CHUNK_SCORE = 2
VALID_EVERY = 5
DEFAULT_TEACHER = "http://localhost:8080"
INTERESTING_KW = [
    "năm", "tháp", "tương truyền", "truyền thuyết", "chúa", "vua",
    "unesco", "độc đáo", "nổi tiếng", "huyền thoại",
]

__all__ = ["chunk_document", "clean_wiki_text", "is_usable", "wiki_url"]


def score_text(text: str, keywords: list[str]) -> int:
    low = text.lower()
    return sum(low.count(k) for k in keywords)


def score_chunk(chunk: dict, keywords: list[str]) -> int:
    return score_text(chunk["heading"], keywords) * 3 + score_text(chunk["text"], keywords)


INTENTS: list[dict] = [
    {
        "id": "tong_quan",
        "q": "Hãy kể chi tiết về {name}",
        "kw": [],
        "prefer_first": True,
        "categories": None,
    },
    {
        "id": "dac_diem",
        "q": "{name} có những đặc điểm gì nổi bật?",
        "kw": ["nổi bật", "đặc trưng", "đặc sắc", "nét", "gồm", "bao gồm",
               "tiêu biểu", "độc đáo", "nổi tiếng", "rộng", "cao", "dài"],
        "categories": None,
    },
    {
        "id": "lich_su",
        "q": "Lịch sử hình thành và phát triển của {name} như thế nào?",
        "kw": ["năm", "thế kỷ", "triều", "vua", "xây dựng", "khởi công",
               "hoàn thành", "lịch sử", "thời", "đời", "trùng tu", "thành lập"],
        "categories": None,
    },
    {
        "id": "y_nghia",
        "q": "{name} có ý nghĩa văn hóa, lịch sử như thế nào?",
        "kw": ["ý nghĩa", "giá trị", "biểu tượng", "tượng trưng", "di sản",
               "unesco", "tín ngưỡng", "tâm linh", "văn hóa", "thờ", "tôn vinh"],
        "categories": None,
    },
    {
        "id": "kien_truc",
        "q": "Kiến trúc, cảnh quan của {name} có gì đặc sắc?",
        "kw": ["kiến trúc", "công trình", "cổng", "điện", "lăng", "mái", "cột",
               "gạch", "đá", "hồ", "vườn", "bố cục", "cảnh quan", "chạm",
               "họa tiết", "trang trí", "tường", "sân", "bậc"],
        "categories": {"Di tích lịch sử", "Danh thắng"},
    },
    {
        "id": "tham_quan",
        "q": "{name} nằm ở đâu?",
        "kw": ["du khách", "tham quan", "khách", "đường", "cách", "km",
               "phía", "tọa lạc", "nằm", "đi", "mùa", "tháng"],
        "categories": None,
    },
    {
        "id": "le_hoi",
        "q": "Có những lễ hội, sự kiện văn hóa nào gắn với {name}?",
        "kw": ["lễ hội", "lễ", "hội", "tế", "rước", "diễn ra", "tổ chức",
               "hằng năm", "âm lịch", "festival", "nghi thức", "cúng"],
        "categories": None,
    },
    {
        "id": "tri_thuc",
        "q": "Có những câu chuyện, truyền thuyết thú vị nào về {name}?",
        "kw": ["truyền thuyết", "tương truyền", "chuyện", "kể rằng", "dân gian",
               "huyền thoại", "sự tích", "tích", "giai thoại", "truyện"],
        "categories": None,
    },
    {
        "id": "bao_ve",
        "q": "Công tác bảo tồn {name} hiện được thực hiện ra sao?",
        "kw": ["bảo tồn", "trùng tu", "tôn tạo", "xếp hạng", "công nhận",
               "di tích", "bảo vệ", "phục hồi", "xuống cấp", "unesco", "quản lý"],
        "categories": None,
    },
    {
        "id": "che_bien",
        "q": "Món {name} được làm từ những nguyên liệu gì và chế biến thế nào?",
        "kw": ["nguyên liệu", "chế biến", "nấu", "bột", "thịt", "tôm", "nước dùng",
               "gia vị", "sợi", "bánh", "rau", "ăn", "vị", "hương", "tô", "bát"],
        "categories": {"Ẩm thực"},
    },
    {
        "id": "bieu_dien",
        "q": "{name} được trình diễn như thế nào?",
        "kw": ["trình diễn", "biểu diễn", "hát", "đàn", "nhạc cụ", "làn điệu",
               "giai điệu", "diễn viên", "nghệ nhân", "sân khấu", "vai", "múa"],
        "categories": {"Nghệ thuật"},
    },
]

INTENTS_BY_ID = {i["id"]: i for i in INTENTS}


def intents_for(category: str) -> list[dict]:
    return [i for i in INTENTS if i["categories"] is None or category in i["categories"]]


def source_url_of(doc: dict) -> str:
    return (doc.get("url") or wiki_url(doc["name"])).strip()


def attach_passage_ids(docs: list[dict]) -> None:
    """Gắn URL dataset lên mỗi chunk — đó là id nguồn lúc train."""
    for doc in docs:
        url = source_url_of(doc)
        doc["url"] = url
        for chunk in doc["chunks"]:
            chunk["id"] = url
            chunk["url"] = url


_GENERIC_TITLES = {"overview", "s0", "s1", "s2", "s3", "s4", "s5"}
_HERITAGE_TITLES = {
    "lang-tu-duc": "Lăng Tự Đức",
    "khiem-lang": "Khiêm Lăng",
}


def _package_doc_name(doc: dict) -> str:
    title = str(doc.get("title") or "").strip()
    if title and title.lower() not in _GENERIC_TITLES:
        return title
    object_key = str(doc.get("object_key") or "")
    for part in object_key.replace("\\", "/").split("/"):
        slug = part.rsplit(".", 1)[0]
        if slug in _HERITAGE_TITLES:
            return _HERITAGE_TITLES[slug]
    return title or str(doc.get("key") or "tài liệu")


def load_package_docs(path: Path) -> tuple[list[dict], list[tuple[str, str]]]:
    """Đọc package R2 → cùng shape docs với bootstrap (name, url, chunks)."""
    package = json.loads(path.read_text(encoding="utf-8"))
    documents = package.get("documents") or []
    passages = package.get("passages") or []
    docs_by_key = {str(doc["key"]): doc for doc in documents if isinstance(doc, dict) and doc.get("key")}
    chunks_by_doc: dict[str, list[dict]] = {key: [] for key in docs_by_key}
    skipped: list[tuple[str, str]] = []
    for passage in passages:
        if not isinstance(passage, dict):
            continue
        doc_key = str(passage.get("document_key") or "")
        if doc_key not in docs_by_key:
            skipped.append((str(passage.get("key") or "?"), "document_key không có trong package"))
            continue
        text = str(passage.get("text") or "").strip()
        if len(text) < 80:
            skipped.append((doc_key, "passage quá ngắn"))
            continue
        chunks_by_doc[doc_key].append({
            "heading": str(docs_by_key[doc_key].get("title") or ""),
            "text": text,
        })
    docs: list[dict] = []
    for key, raw in docs_by_key.items():
        url = str(raw.get("source_url") or "").strip()
        name = _package_doc_name(raw)
        chunks = chunks_by_doc.get(key) or []
        if not url:
            skipped.append((name, "thiếu source_url"))
            continue
        if not chunks:
            skipped.append((name, "không có passage"))
            continue
        docs.append({
            "name": name,
            "category": "",
            "region": str(raw.get("region") or ""),
            "url": url,
            "chunks": chunks,
        })
    return docs, skipped


def passage_block(chunk: dict) -> str:
    return f"[Passage {chunk['id']}]\n{chunk['text']}"


def assistant_json(answer: str, source_ids: list[str], follow_ups: list[str]) -> str:
    return json.dumps(
        {
            "answer": answer.strip(),
            "source_ids": source_ids,
            "follow_up_questions": follow_ups[:3],
        },
        ensure_ascii=False,
    )


def conversation_sample(
    source: str,
    question: str,
    answer: str,
    source_ids: list[str],
    follow_ups: list[str],
) -> dict[str, Any]:
    return {"messages": [
        {"role": "system", "content": CONVERSATION_SYSTEM},
        {"role": "user", "content": user_msg(source, question)},
        {"role": "assistant", "content": assistant_json(answer, source_ids, follow_ups)},
    ]}


def make_qa_sample(chunk: dict, question: str, answer: str, follow_ups: list[str]) -> dict[str, Any]:
    pid = chunk["id"]
    return conversation_sample(passage_block(chunk), question, answer, [pid], follow_ups)


def compose_answer(sents: list[str], extra: str | None = None) -> str:
    parts = [s.strip() for s in sents if s.strip()]
    extra = (extra or "").strip()
    if extra and extra not in parts:
        parts.append(extra)
    return " ".join(parts)


def extra_sentence(chunk: dict, already: list[str]) -> str | None:
    rest = [s for s in sentences(chunk["text"]) if s not in already]
    scored = [(score_text(s, INTERESTING_KW), s) for s in rest]
    scored = [item for item in scored if item[0] > 0]
    if not scored:
        return None
    return max(scored, key=lambda item: item[0])[1]


def follow_up_questions(doc: dict, current_id: str, rng: random.Random) -> list[str]:
    others = [intent for intent in intents_for(doc["category"]) if intent["id"] != current_id]
    rng.shuffle(others)
    questions = [intent["q"].format(name=doc["name"]) for intent in others]
    extra = [f"{doc['name']} gắn với nhân vật nào?", f"{doc['name']} có gì đặc biệt?"]
    merged: list[str] = []
    for question in questions + extra:
        if question not in merged:
            merged.append(question)
        if len(merged) == 3:
            break
    return merged[:3]


MAX_QUOTE_CHARS = 260


def pick_sentences(chunk: dict, keywords: list[str], k: int = 4) -> list[str]:
    sents = sentences(chunk["text"])
    if not sents:
        return []
    if not keywords:
        return sents[:k]
    scored = [(score_text(s, keywords), i, s) for i, s in enumerate(sents)]
    hits = [t for t in scored if t[0] > 0]
    top = sorted(hits or scored, key=lambda t: (-t[0], t[1]))[:k]
    return [s for _, _, s in sorted(top, key=lambda t: t[1])]


def make_quote(chunk: dict, picked: list[str], keywords: list[str]) -> str:
    """Giữ cho bootstrap_v3 import; không dùng trong mẫu hội thoại."""
    pool = picked + [s for s in sentences(chunk["text"]) if s not in picked]
    fits = [s for s in pool if len(s) <= MAX_QUOTE_CHARS]
    if fits:
        return max(fits, key=lambda s: (score_text(s, keywords), -len(s)))
    longest = pool[0]
    cut = longest.rfind(" ", 0, MAX_QUOTE_CHARS)
    return longest[: cut if cut > 0 else MAX_QUOTE_CHARS].rstrip(" ,;:") + " ..."


NO_SOURCE_QUESTIONS = [
    "Hát chầu văn có nguồn gốc từ đâu?",
    "Múa rối nước phổ biến ở vùng nào?",
    "Quan họ là di sản của tỉnh nào?",
    "Lễ hội Lim được tổ chức vào thời gian nào?",
    "Cải lương xuất hiện từ bao giờ?",
    "Phố cổ Hội An có bao nhiêu di tích được xếp hạng?",
    "Làng gốm Bát Tràng thuộc tỉnh nào?",
    "Thánh địa Mỹ Sơn được xây dựng vào thời kỳ nào?",
    "Đờn ca tài tử được UNESCO công nhận năm nào?",
    "Hát xoan bắt nguồn từ đâu?",
    "Chợ Bến Thành được xây dựng năm nào?",
    "Vịnh Hạ Long có diện tích bao nhiêu?",
    "Ca trù khác gì với hát ả đào?",
    "Lễ hội Đền Hùng diễn ra ngày nào?",
    "Tranh Đông Hồ được in bằng chất liệu gì?",
    "Nhà rông Tây Nguyên có đặc điểm gì?",
]

NO_SOURCE_ANSWERS = [
    "Mình chưa có hồ sơ về nội dung này nên chưa xác nhận được.",
    "Câu này nằm ngoài tư liệu Huế – Đà Nẵng đang có.",
    "Hiện không có đoạn nguồn để trả lời, mình không suy đoán.",
]

NO_SOURCE_FOLLOW_UPS = [
    "Bạn đang hỏi di sản nào ở Huế?",
    "Hay một địa điểm ở Đà Nẵng?",
    "Bạn muốn tìm hiểu ẩm thực Huế?",
]

OFF_TOPIC_QUESTIONS = [
    ("giá vé tham quan", "Giá vé tham quan {name} hiện nay là bao nhiêu?",
     ["giá vé", "vé vào", "đồng/vé", "nghìn đồng", "vnđ"]),
    ("khoảng cách tới sân bay", "{name} cách sân bay bao nhiêu ki-lô-mét?",
     ["sân bay"]),
    ("số lượt khách năm 2024", "Năm 2024 {name} đón bao nhiêu lượt khách?",
     ["2024", "lượt khách"]),
    ("giờ mở cửa", "{name} mở cửa từ mấy giờ đến mấy giờ?",
     ["mở cửa", "giờ", "đóng cửa"]),
    ("thông tin liên hệ", "Ban quản lý {name} có số điện thoại liên hệ nào?",
     ["điện thoại", "hotline", "liên hệ"]),
    ("chỗ lưu trú", "Gần {name} có những khách sạn nào?",
     ["khách sạn", "resort", "lưu trú", "homestay"]),
]

OFF_TOPIC_ANSWERS = [
    "Đoạn này nói về {name} nhưng không có thông tin về {topic}, nên mình chưa xác nhận được phần đó.",
    "Tư liệu không ghi {topic} của {name}. Mình không suy đoán.",
    "Mình đọc đoạn nguồn rồi, không thấy {topic} của {name}.",
]

WRONG_DOC_QUESTIONS = [
    "Hãy kể chi tiết về {name}",
    "{name} có ý nghĩa văn hóa, lịch sử như thế nào?",
    "Lịch sử hình thành và phát triển của {name} như thế nào?",
    "{name} có những đặc điểm gì nổi bật?",
]

WRONG_DOC_ANSWERS = [
    "Đoạn đang có là về {other}, không phải {name}. Mình không lấy thông tin của {other} để trả lời.",
    "Nguồn này nói về {other}, không có nội dung về {name}.",
    "Đây là tư liệu {other} chứ không phải {name}, nên mình chưa xác nhận được.",
]


def make_no_source_samples(rng: random.Random, questions: list[str]) -> list[dict]:
    out = []
    for question in questions:
        follow = list(NO_SOURCE_FOLLOW_UPS)
        rng.shuffle(follow)
        out.append(conversation_sample(
            "(không có)", question, rng.choice(NO_SOURCE_ANSWERS), [], follow[:2],
        ))
    return out


def make_off_topic_samples(rng: random.Random, docs: list[dict], per_doc: int = 1) -> list[dict]:
    out: list[dict] = []
    for doc in docs:
        picked = 0
        pool = list(OFF_TOPIC_QUESTIONS)
        rng.shuffle(pool)
        for topic, q_tpl, markers in pool:
            if picked >= per_doc:
                break
            chunk = rng.choice(doc["chunks"])
            if score_text(chunk["text"], markers) > 0:
                continue
            question = q_tpl.format(name=doc["name"])
            answer = rng.choice(OFF_TOPIC_ANSWERS).format(name=doc["name"], topic=topic)
            out.append(conversation_sample(
                passage_block(chunk), question, answer, [],
                follow_up_questions(doc, "tham_quan", rng),
            ))
            picked += 1
    return out


def make_wrong_doc_samples(rng: random.Random, docs: list[dict], per_doc: int = 1) -> list[dict]:
    out: list[dict] = []
    for doc in docs:
        others = [item for item in docs if item["name"] != doc["name"]]
        rng.shuffle(others)
        picked = 0
        for other in others:
            if picked >= per_doc:
                break
            chunk = rng.choice(other["chunks"])
            if contains_name(strip_accents(chunk["text"]), doc["name"]):
                continue
            question = rng.choice(WRONG_DOC_QUESTIONS).format(name=doc["name"])
            answer = rng.choice(WRONG_DOC_ANSWERS).format(name=doc["name"], other=other["name"])
            out.append(conversation_sample(
                passage_block(chunk), question, answer, [],
                follow_up_questions(doc, "tong_quan", rng),
            ))
            picked += 1
    return out


FALSE_PREMISE = [
    (
        "{name} ở Hà Nội đúng không?",
        "Hà Nội",
        "{name} không ở Hà Nội. {body}",
    ),
    (
        "{name} được xây năm 2010 phải không?",
        "2010",
        "Không có mốc 2010 trong tư liệu về {name}. {body}",
    ),
]


def make_false_premise_samples(rng: random.Random, docs: list[dict], per_doc: int = 1) -> list[dict]:
    out: list[dict] = []
    for doc in docs:
        added = 0
        templates = list(FALSE_PREMISE)
        rng.shuffle(templates)
        for question_tpl, marker, answer_tpl in templates:
            if added >= per_doc:
                break
            chunk = doc["chunks"][0]
            if marker.lower() in chunk["text"].lower():
                continue
            sents = pick_sentences(chunk, ["nằm", "tọa lạc", "phường", "năm", "xây"]) or pick_sentences(chunk, [])
            if not sents:
                continue
            body = compose_answer(sents[:3])
            if marker in body:
                continue
            question = question_tpl.format(name=doc["name"])
            answer = answer_tpl.format(name=doc["name"], body=body)
            out.append(make_qa_sample(
                chunk, question, answer, follow_up_questions(doc, "tong_quan", rng),
            ))
            added += 1
    return out


NER_MIN_LABELS = 3
NER_PER_DOC = 4
NER_SENT_CHARS = (60, 400)


def make_ner_samples(rng: random.Random, docs: list[dict], per_doc: int = NER_PER_DOC) -> list[dict]:
    """NER giữ SYSTEM cũ: object 4 khóa, không trộn schema hội thoại."""
    from apps.backend.core.nerlabel import allowed_names, n_labels, ner_label

    out: list[dict] = []
    for doc in docs:
        full = " ".join(c["heading"] + " " + c["text"] for c in doc["chunks"])
        allowed = allowed_names(full)
        cands: list[tuple[int, str, dict]] = []
        weak: list[tuple[int, str, dict]] = []
        for chunk in doc["chunks"]:
            for sent in sentences(chunk["text"]):
                if not NER_SENT_CHARS[0] <= len(sent) <= NER_SENT_CHARS[1]:
                    continue
                label = ner_label(sent, allowed)
                n = n_labels(label)
                if n >= NER_MIN_LABELS:
                    cands.append((sum(1 for v in label.values() if v), sent, label))
                elif n >= 2:
                    weak.append((sum(1 for v in label.values() if v), sent, label))
        rng.shuffle(cands)
        cands.sort(key=lambda t: -t[0])
        picked = cands[:per_doc]
        for entity_type in NER_TYPES:
            if any(lab[entity_type] for _, _, lab in picked):
                continue
            extra = next((c for c in cands + weak if c[2][entity_type]), None)
            if extra:
                picked.append(extra)
        others = [item for item in docs if item["name"] != doc["name"]] or docs
        for _, sent, label in picked:
            source = "(không có)" if rng.random() < 0.5 else rng.choice(
                rng.choice(others)["chunks"])["text"]
            out.append({"messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_msg(source, NER_QUESTION.format(text=sent))},
                {"role": "assistant", "content": json.dumps(
                    {t: label[t] for t in NER_TYPES}, ensure_ascii=False)},
            ]})
    return out


TEACHER_SYSTEM = """Bạn viết lại các câu tư liệu thành lời một người am hiểu đang trả lời khách.
TUYỆT ĐỐI KHÔNG thêm thông tin, số, năm, tên người hay địa danh không có trong tư liệu.
Không chào, không mời tham quan, không viết "Theo tài liệu", không trích nguồn, không gạch đầu dòng.
Chỉ trả về đúng một đoạn văn."""

NUM_RE = re.compile(r"\d+")
REFUSAL_HINTS = ("không tìm thấy", "không có thông tin", "không đề cập",
                 "xin phép không", "ngoài phạm vi", "không được cung cấp")


def teacher_generate(
    base_url: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float = 0.0,
) -> str:
    import httpx

    response = httpx.post(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        json={
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=300.0,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def faithful(answer: str, source: str, allow: tuple[str, ...] = ()) -> str:
    """Trả "" nếu answer chỉ dùng thông tin có trong nguồn."""
    if len(answer) < 40:
        return "quá ngắn"
    low = answer.lower()
    if any(h in low for h in REFUSAL_HINTS):
        return "teacher đi từ chối"
    for num in sorted(set(NUM_RE.findall(answer))):
        if num not in source:
            return f"số {num!r} không có trong nguồn"
    src_plain = strip_accents(source)
    allow_plain = tuple(strip_accents(a) for a in allow)
    for name in extract_names(answer):
        plain = strip_accents(name)
        if any(plain in a or a in plain for a in allow_plain):
            continue
        if not contains_name(src_plain, name):
            return f"tên {name!r} không có trong nguồn"
    return ""


def teacher_rewrite(model_path: str, name: str, question: str, sents: list[str],
                    stats: Counter, max_tokens: int = 420) -> str | None:
    source = " ".join(sents)
    messages = [
        {"role": "system", "content": TEACHER_SYSTEM},
        {"role": "user", "content": f"Câu hỏi cần trả lời: {question}\n\nTư liệu:\n{source}"},
    ]
    try:
        text = teacher_generate(model_path, messages, max_tokens=max_tokens)
    except Exception as exc:  # noqa: BLE001
        print(f"    [WARN] teacher lỗi: {exc}")
        stats["lỗi"] += 1
        return None
    text = (text or "").strip()
    reason = faithful(text, source, allow=(name,))
    if reason:
        stats[reason.split(" không")[0] if "không có trong nguồn" in reason else reason] += 1
        return None
    stats["nhận"] += 1
    return text

def pick_chunk(chunks: list[dict], used: set[int], intent: dict) -> tuple[int, dict] | None:
    if intent.get("prefer_first"):
        return (0, chunks[0]) if chunks else None

    def best_of(pool: list[tuple[int, dict]]) -> tuple[int, dict] | None:
        if not pool:
            return None
        idx, chunk = max(pool, key=lambda ic: (score_chunk(ic[1], intent["kw"]), -ic[0]))
        return (idx, chunk) if score_chunk(chunk, intent["kw"]) >= MIN_CHUNK_SCORE else None

    unused = [(i, c) for i, c in enumerate(chunks) if i not in used]
    return best_of(unused) or best_of(list(enumerate(chunks)))


def generate_for_doc(doc: dict, rng: random.Random, teacher: str | None,
                     stats: Counter) -> tuple[list[dict], list[str]]:
    samples: list[dict] = []
    skipped: list[str] = []
    used: set[int] = set()

    for intent in intents_for(doc["category"]):
        picked = pick_chunk(doc["chunks"], used, intent)
        if picked is None:
            skipped.append(intent["id"])
            continue
        idx, chunk = picked
        used.add(idx)
        question = intent["q"].format(name=doc["name"])
        sents = pick_sentences(chunk, intent["kw"])
        if not sents:
            skipped.append(intent["id"])
            continue
        extra = extra_sentence(chunk, sents) if rng.random() < 0.7 else None
        material = sents + ([extra] if extra else [])
        body = teacher_rewrite(teacher, doc["name"], question, material, stats) if teacher else None
        answer = body or compose_answer(sents, extra)
        samples.append(make_qa_sample(
            chunk, question, answer, follow_up_questions(doc, intent["id"], rng),
        ))
    return samples, skipped


def split_docs(docs: list[dict]) -> tuple[list[dict], list[dict]]:
    """Chia theo tài liệu (url), không theo tên hiển thị — nhiều file cùng di sản."""
    valid = [d for i, d in enumerate(docs) if i % VALID_EVERY == 2]
    valid_keys = {d.get("url") or d["name"] for d in valid}
    train = [d for d in docs if (d.get("url") or d["name"]) not in valid_keys]
    return train, valid


def build_split(docs: list[dict], no_source_qs: list[str], rng: random.Random,
                teacher: str | None, stats: Counter) -> list[dict]:
    samples: list[dict] = []
    for doc in docs:
        got, skipped = generate_for_doc(doc, rng, teacher, stats)
        samples.extend(got)
        note = f" (bỏ: {', '.join(skipped)})" if skipped else ""
        print(f"  {doc['name']:<34} {len(got):>2} mẫu{note}")

    extra = {
        "refusal không nguồn": make_no_source_samples(rng, no_source_qs),
        "refusal nguồn thiếu ý": make_off_topic_samples(rng, docs),
        "refusal nguồn sai bài": make_wrong_doc_samples(rng, docs),
        "giả định sai": make_false_premise_samples(rng, docs),
    }
    for label, rows in extra.items():
        print(f"  + {label:<24} {len(rows):>2} mẫu")
        samples.extend(rows)
    rng.shuffle(samples)
    return samples


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def source_of(row: dict) -> str:
    return row["messages"][1]["content"].split("\n\nCâu hỏi:")[0]


def assistant_obj(row: dict) -> dict | None:
    try:
        obj = json.loads(row["messages"][-1]["content"])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def dedupe(rows: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for row in rows:
        key = (row["messages"][1]["content"], row["messages"][2]["content"])
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def drop_leaked(valid_rows: list[dict], train_rows: list[dict]) -> list[dict]:
    train_sources = {source_of(r) for r in train_rows}
    return [r for r in valid_rows
            if source_of(r) == "Nguồn: (không có)" or source_of(r) not in train_sources]


def count_refusals(rows: list[dict]) -> int:
    n = 0
    for row in rows:
        obj = assistant_obj(row)
        if obj is not None and "source_ids" in obj:
            if obj.get("source_ids") == []:
                n += 1
            continue
        text = row["messages"][-1]["content"]
        if any(m in text for m in ("chưa xác nhận", "không suy đoán", "không phải")):
            n += 1
    return n


def count_ner(rows: list[dict]) -> int:
    return sum(1 for r in rows if r["messages"][1]["content"].count(NER_QUESTION[:20]))


def ner_type_coverage(rows: list[dict]) -> dict[str, int]:
    cover = {t: 0 for t in NER_TYPES}
    for row in rows:
        if not row["messages"][1]["content"].count(NER_QUESTION[:20]):
            continue
        try:
            label = json.loads(row["messages"][-1]["content"])
        except json.JSONDecodeError:
            continue
        for entity_type in NER_TYPES:
            if label.get(entity_type):
                cover[entity_type] += 1
    return cover


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE,
                        help="package.json ingestion R2")
    parser.add_argument("--use-model", action="store_true",
                        help="dùng LLM local viết lại câu đã chọn (cổng faithful)")
    parser.add_argument("--model", default=DEFAULT_TEACHER,
                        help=f"URL llama.cpp teacher khi --use-model (mặc định: {DEFAULT_TEACHER})")
    args = parser.parse_args()

    package = args.package
    if not package.is_file():
        print(f"ERROR: chưa có {package}. Chạy ingest_r2 rồi truyền --package.")
        sys.exit(1)

    rng = random.Random(SEED)
    docs, skipped_docs = load_package_docs(package)
    if not docs:
        print("ERROR: không có tài liệu nào dùng được.")
        sys.exit(1)
    attach_passage_ids(docs)

    print(f"=== Package: {package} ===")

    print(f"=== Corpus: {len(docs)} tài liệu dùng được, {len(skipped_docs)} bị bỏ ===")
    for name, reason in skipped_docs:
        print(f"  - bỏ {name}: {reason}")

    teacher = args.model if args.use_model else None
    if teacher:
        print(f"\n=== Teacher: {teacher} (chỉ viết lại, có cổng trung thực) ===")
    else:
        print("\n=== Ghép câu từ nguồn (thêm --use-model để viết lại cho mượt) ===")

    stats: Counter = Counter()
    train_docs, valid_docs = split_docs(docs)
    cut = len(NO_SOURCE_QUESTIONS) * (VALID_EVERY - 1) // VALID_EVERY

    print(f"\n--- TRAIN ({len(train_docs)} địa điểm) ---")
    train_rows = dedupe(build_split(train_docs, NO_SOURCE_QUESTIONS[:cut], rng, teacher, stats))
    print(f"\n--- VALID ({len(valid_docs)} địa điểm, tách riêng khỏi train) ---")
    valid_rows = dedupe(build_split(valid_docs, NO_SOURCE_QUESTIONS[cut:], rng, teacher, stats))
    leaked = len(valid_rows)
    valid_rows = drop_leaked(valid_rows, train_rows)
    if leaked != len(valid_rows):
        print(f"\n  bỏ {leaked - len(valid_rows)} mẫu valid dùng chung đoạn nguồn với train")

    write_jsonl(OUT_TRAIN, train_rows)
    write_jsonl(OUT_VALID, valid_rows)

    if stats:
        print("\n=== Teacher ===")
        for reason, n in stats.most_common():
            print(f"  {reason:<40} {n}")

    print("\n=== Done ===")
    for label, rows, path in (("Train", train_rows, OUT_TRAIN), ("Valid", valid_rows, OUT_VALID)):
        ref = count_refusals(rows)
        print(f"  {label}: {len(rows):>3} mẫu | {ref} refusal ({ref / len(rows):.0%})  → {path}")
    print(f"\n  Gợi ý iters (batch 1, accum 8, ~3 epoch): "
          f"{max(len(train_rows) * 3, 100)}")


if __name__ == "__main__":
    main()
