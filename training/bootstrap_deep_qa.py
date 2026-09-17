#!/usr/bin/env python3
"""
Sinh training data deep-QA cho chatbot văn hóa Huế - Đà Nẵng.

Sửa so với bản cũ (những lỗi làm data dạy sai):
- Chunk được CHỌN theo độ liên quan với loại câu hỏi, không random. Tài liệu nào
  không có nội dung cho loại câu hỏi đó thì bỏ qua, không sinh mẫu lệch nội dung.
- Câu trả lời ghép từ các câu trong chunk khớp ý câu hỏi (bản cũ luôn copy 2 câu
  đầu chunk bất kể hỏi gì).
- Trích dẫn là câu trọn vẹn, không cắt cụt giữa từ ở mốc 100 ký tự.
- Làm sạch rác Wikipedia (Xem thêm / Tham khảo / Liên kết ngoài / Hình ảnh...).
- Bỏ trang định hướng và tài liệu quá ngắn, khử trùng lặp nội dung.
- Chia train/valid theo ĐỊA ĐIỂM để valid không rò rỉ từ train.
- Refusal: sửa lỗi chỉ sinh 7 mẫu khi yêu cầu 40, bỏ URL Hội An bịa trong mọi
  câu từ chối, và thêm loại refusal quan trọng nhất: CÓ nguồn nhưng nguồn không
  chứa câu trả lời.

Chạy:
  python training/bootstrap_deep_qa.py
  python training/bootstrap_deep_qa.py --use-model    # dùng llama.cpp server làm teacher
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Chunker/loader dùng CHUNG với serving. Nếu file này tự chunk lại theo bản sao
# riêng thì đoạn `Nguồn:` lúc train sẽ khác đoạn `Nguồn:` lúc chạy thật - đúng
# loại lệch train/serve làm fine-tune mất tác dụng.
from backend.core.corpus import (  # noqa: E402
    INDEX_FILE,
    chunk_document,
    clean_wiki_text,
    is_usable,
    load_docs,
    wiki_url,
)
from backend.core.kg import extract_names  # noqa: E402
from backend.core.nerlabel import allowed_names, n_labels, ner_label  # noqa: E402

# SYSTEM prompt và cách ghép user message ĐẶT MỘT CHỖ DUY NHẤT (backend/core/prompt.py)
# và được import ở cả train, serve (llm.py) và eval (score_gold.py). Bản cũ copy
# chuỗi này ở 3 file với 3 nội dung khác nhau.
from backend.core.prompt import NER_QUESTION, NER_TYPES, SYSTEM, user_msg  # noqa: E402
from backend.core.textutil import contains_name, sentences, strip_accents  # noqa: E402

OUT_TRAIN = ROOT / "data" / "train.jsonl"
OUT_VALID = ROOT / "data" / "valid.jsonl"

SEED = 42
MIN_CHUNK_SCORE = 2         # dưới mức này coi như chunk không trả lời được câu hỏi
VALID_EVERY = 5             # 1/5 địa điểm dành cho valid

__all__ = ["chunk_document", "clean_wiki_text", "is_usable", "wiki_url"]  # tương thích import cũ

DEFAULT_TEACHER = "http://localhost:8080"


def score_text(text: str, keywords: list[str]) -> int:
    low = text.lower()
    return sum(low.count(k) for k in keywords)


def score_chunk(chunk: dict, keywords: list[str]) -> int:
    # tiêu đề mục là tín hiệu mạnh nhất về chủ đề của chunk
    return score_text(chunk["heading"], keywords) * 3 + score_text(chunk["text"], keywords)


# --- Các loại câu hỏi -------------------------------------------------------
# kw: từ khóa để chọn chunk & câu trả lời đúng ý câu hỏi.
# categories: None = áp dụng cho mọi loại địa điểm.
# leads: câu dẫn (đổi luân phiên để model không học cứng một khuôn câu).

INTENTS: list[dict] = [
    {
        "id": "tong_quan",
        "q": "Hãy kể chi tiết về {name}",
        "kw": [],
        "prefer_first": True,   # phần mở đầu bài Wikipedia chính là phần tổng quan
        "categories": None,
        "leads": [
            "Xin được giới thiệu đôi nét về {name}.",
            "Theo tư liệu hiện có, {name} được ghi nhận như sau.",
            "Nói đến {name}, nguồn tư liệu cho biết:",
        ],
    },
    {
        "id": "dac_diem",
        "q": "{name} có những đặc điểm gì nổi bật?",
        "kw": ["nổi bật", "đặc trưng", "đặc sắc", "nét", "gồm", "bao gồm",
               "tiêu biểu", "độc đáo", "nổi tiếng", "rộng", "cao", "dài"],
        "categories": None,
        "leads": [
            "Những nét làm nên đặc trưng của {name} được tư liệu ghi lại:",
            "Về những điểm nổi bật của {name}:",
            "Điều khiến {name} được nhắc đến nhiều nằm ở chỗ:",
        ],
    },
    {
        "id": "lich_su",
        "q": "Lịch sử hình thành và phát triển của {name} như thế nào?",
        "kw": ["năm", "thế kỷ", "triều", "vua", "xây dựng", "khởi công",
               "hoàn thành", "lịch sử", "thời", "đời", "trùng tu", "thành lập"],
        "categories": None,
        "leads": [
            "Lịch sử {name} được tư liệu ghi lại như sau.",
            "Về quá trình hình thành của {name}:",
            "Dòng thời gian của {name} hiện ra qua những ghi chép sau:",
        ],
    },
    {
        "id": "y_nghia",
        "q": "{name} có ý nghĩa văn hóa, lịch sử như thế nào?",
        "kw": ["ý nghĩa", "giá trị", "biểu tượng", "tượng trưng", "di sản",
               "unesco", "tín ngưỡng", "tâm linh", "văn hóa", "thờ", "tôn vinh"],
        "categories": None,
        "leads": [
            "Giá trị văn hóa của {name} được tư liệu nói tới ở những điểm sau:",
            "Về ý nghĩa của {name}:",
            "{name} mang ý nghĩa được ghi nhận như sau:",
        ],
    },
    {
        "id": "kien_truc",
        "q": "Kiến trúc, cảnh quan của {name} có gì đặc sắc?",
        "kw": ["kiến trúc", "công trình", "cổng", "điện", "lăng", "mái", "cột",
               "gạch", "đá", "hồ", "vườn", "bố cục", "cảnh quan", "chạm",
               "họa tiết", "trang trí", "tường", "sân", "bậc"],
        "categories": {"Di tích lịch sử", "Danh thắng"},
        "leads": [
            "Về kiến trúc và cảnh quan của {name}, tư liệu mô tả:",
            "Diện mạo kiến trúc của {name} hiện ra như sau:",
            "Nét kiến trúc đáng chú ý của {name}:",
        ],
    },
    {
        "id": "tham_quan",
        "q": "Du khách đến tham quan {name} cần lưu ý những gì?",
        "kw": ["du khách", "tham quan", "khách", "đường", "cách", "km",
               "phía", "tọa lạc", "nằm", "đi", "mùa", "tháng"],
        "categories": None,
        "leads": [
            "Với du khách muốn đến {name}, tư liệu cho biết:",
            "Một vài thông tin tham quan {name} theo nguồn:",
            "Về vị trí và việc tham quan {name}:",
        ],
    },
    {
        "id": "le_hoi",
        "q": "Có những lễ hội, sự kiện văn hóa nào gắn với {name}?",
        "kw": ["lễ hội", "lễ", "hội", "tế", "rước", "diễn ra", "tổ chức",
               "hằng năm", "âm lịch", "festival", "nghi thức", "cúng"],
        "categories": None,
        "leads": [
            "Về các lễ hội, sự kiện gắn với {name}:",
            "Sinh hoạt lễ hội quanh {name} được ghi nhận:",
            "Nguồn tư liệu nhắc đến những dịp lễ sau ở {name}:",
        ],
    },
    {
        "id": "tri_thuc",
        "q": "Có những câu chuyện, truyền thuyết thú vị nào về {name}?",
        "kw": ["truyền thuyết", "tương truyền", "chuyện", "kể rằng", "dân gian",
               "huyền thoại", "sự tích", "tích", "giai thoại", "truyện"],
        "categories": None,
        "leads": [
            "Quanh {name} còn lưu lại những câu chuyện sau:",
            "Về giai thoại gắn với {name}:",
            "Tư liệu có ghi lại chuyện kể về {name}:",
        ],
    },
    {
        "id": "bao_ve",
        "q": "Công tác bảo tồn {name} hiện được thực hiện ra sao?",
        "kw": ["bảo tồn", "trùng tu", "tôn tạo", "xếp hạng", "công nhận",
               "di tích", "bảo vệ", "phục hồi", "xuống cấp", "unesco", "quản lý"],
        "categories": None,
        "leads": [
            "Về công tác bảo tồn {name}:",
            "Tình trạng bảo tồn {name} được tư liệu ghi nhận:",
            "Nguồn cho biết {name} được giữ gìn như sau:",
        ],
    },
    {
        "id": "che_bien",
        "q": "Món {name} được làm từ những nguyên liệu gì và chế biến thế nào?",
        "kw": ["nguyên liệu", "chế biến", "nấu", "bột", "thịt", "tôm", "nước dùng",
               "gia vị", "sợi", "bánh", "rau", "ăn", "vị", "hương", "tô", "bát"],
        "categories": {"Ẩm thực"},
        "leads": [
            "Về nguyên liệu và cách chế biến {name}:",
            "Món {name} được tư liệu mô tả:",
            "Cách làm nên hương vị {name}:",
        ],
    },
    {
        "id": "bieu_dien",
        "q": "{name} được trình diễn như thế nào?",
        "kw": ["trình diễn", "biểu diễn", "hát", "đàn", "nhạc cụ", "làn điệu",
               "giai điệu", "diễn viên", "nghệ nhân", "sân khấu", "vai", "múa"],
        "categories": {"Nghệ thuật"},
        "leads": [
            "Về cách trình diễn {name}:",
            "Hình thức diễn xướng của {name} được ghi lại:",
            "Nguồn mô tả lối biểu diễn {name} như sau:",
        ],
    },
]

INTENTS_BY_ID = {i["id"]: i for i in INTENTS}


def intents_for(category: str) -> list[dict]:
    return [i for i in INTENTS if i["categories"] is None or category in i["categories"]]


# --- Dựng câu trả lời -------------------------------------------------------

MAX_QUOTE_CHARS = 260


def pick_sentences(chunk: dict, keywords: list[str], k: int = 4) -> list[str]:
    """Lấy tối đa k câu khớp ý câu hỏi, giữ nguyên thứ tự trong nguồn."""
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
    """Trích dẫn phải là câu TRỌN VẸN; chỉ cắt ở ranh giới từ nếu không còn cách."""
    pool = picked + [s for s in sentences(chunk["text"]) if s not in picked]
    fits = [s for s in pool if len(s) <= MAX_QUOTE_CHARS]
    if fits:
        return max(fits, key=lambda s: (score_text(s, keywords), -len(s)))
    longest = pool[0]
    cut = longest.rfind(" ", 0, MAX_QUOTE_CHARS)
    return longest[: cut if cut > 0 else MAX_QUOTE_CHARS].rstrip(" ,;:") + " ..."


def build_answer(name: str, intent: dict, chunk: dict, url: str, rng: random.Random,
                 sents: list[str] | None = None) -> str | None:
    sents = sents if sents is not None else pick_sentences(chunk, intent["kw"])
    if not sents:
        return None
    lead = rng.choice(intent["leads"]).format(name=name)
    body = " ".join(sents)
    quote = make_quote(chunk, sents, intent["kw"])
    return f"{lead} {body} [Nguồn: {quote} — {url}]"



# --- Refusal ----------------------------------------------------------------

# Câu hỏi nằm ngoài phạm vi corpus Huế - Đà Nẵng (không có nguồn kèm theo)
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
    "Rất tiếc, nguồn tư liệu được cung cấp không có thông tin về nội dung này, "
    "nên tôi chưa thể trả lời. Nếu bạn bổ sung tài liệu liên quan, tôi sẽ trích "
    "dẫn và trả lời chính xác hơn.",
    "Trong nguồn hiện có không đề cập tới điều bạn hỏi, vì vậy tôi xin phép "
    "không suy đoán. Bạn vui lòng cung cấp thêm tư liệu để tôi trả lời có căn cứ.",
    "Tôi không tìm thấy thông tin này trong nguồn được cung cấp. Để tránh đưa ra "
    "thông tin không có cơ sở, tôi xin dừng ở đây và mong bạn bổ sung tài liệu.",
]

# Câu hỏi CÓ nguồn nhưng nguồn không chứa câu trả lời - trường hợp khó và quan
# trọng nhất: model phải đọc nguồn rồi nhận ra nguồn thiếu thông tin.
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
    "Nguồn được cung cấp nói về {name} nhưng không đề cập tới {topic}, "
    "nên tôi không có căn cứ để trả lời phần này. Bạn vui lòng bổ sung tư liệu "
    "cụ thể hơn để tôi trả lời chính xác.",
    "Đoạn tư liệu trên không chứa thông tin về {topic} của {name}. Tôi xin phép "
    "không suy đoán, và mong bạn cung cấp thêm nguồn về nội dung này.",
    "Tôi đã đọc nguồn nhưng không thấy nội dung nào nói về {topic} của {name}. "
    "Để tránh đưa thông tin sai, tôi xin dừng ở đây.",
]


def make_no_source_samples(rng: random.Random, questions: list[str]) -> list[dict]:
    return [
        {"messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_msg("(không có)", q)},
            {"role": "assistant", "content": rng.choice(NO_SOURCE_ANSWERS)},
        ]}
        for q in questions
    ]


def make_off_topic_samples(rng: random.Random, docs: list[dict], per_doc: int = 1) -> list[dict]:
    """Nguồn thật + câu hỏi mà nguồn đó không trả lời được."""
    out: list[dict] = []
    for doc in docs:
        picked = 0
        for topic, q_tpl, markers in rng.sample(OFF_TOPIC_QUESTIONS, len(OFF_TOPIC_QUESTIONS)):
            if picked >= per_doc:
                break
            chunk = rng.choice(doc["chunks"])
            # chỉ dùng khi nguồn thật sự KHÔNG chứa thông tin được hỏi
            if score_text(chunk["text"], markers) > 0:
                continue
            answer = rng.choice(OFF_TOPIC_ANSWERS).format(name=doc["name"], topic=topic)
            out.append({"messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_msg(chunk["text"], q_tpl.format(name=doc["name"]))},
                {"role": "assistant", "content": answer},
            ]})
            picked += 1
    return out


# Nguồn là tư liệu của MỘT DI SẢN KHÁC - đúng lỗi hệ gặp thật khi retrieval trượt
# bài ("Đàn Nam Giao thờ ai?" -> chunk của Nhã nhạc cung đình Huế, coverage 1.00).
# Trước đây trường hợp này chỉ được chặn bởi cổng REQUIRE_EVIDENCE_FOR_NAMED trong
# rag.py, model chưa từng thấy một ví dụ nào: an toàn nằm trong một câu `if` chứ
# không nằm trong trọng số. Cổng kia cũng lọt khi chunk sai bài tình cờ nhắc tên.
WRONG_DOC_QUESTIONS = [
    "Hãy kể chi tiết về {name}",
    "{name} có ý nghĩa văn hóa, lịch sử như thế nào?",
    "Lịch sử hình thành và phát triển của {name} như thế nào?",
    "{name} có những đặc điểm gì nổi bật?",
]

WRONG_DOC_ANSWERS = [
    "Đoạn tư liệu được cung cấp nói về {other}, không đề cập tới {name}. Vì chưa "
    "có nguồn về {name}, tôi xin phép không trả lời để tránh lẫn thông tin của "
    "hai di sản khác nhau.",
    "Nguồn trên là tư liệu về {other}; trong đó không có nội dung nào về {name}. "
    "Tôi xin không suy đoán, mong bạn bổ sung tài liệu đúng về {name}.",
    "Tôi đã đọc nguồn, nhưng đây là tư liệu về {other} chứ không phải {name}. Để "
    "tránh đưa thông tin của một di sản khác, tôi xin dừng ở đây.",
]


def make_wrong_doc_samples(rng: random.Random, docs: list[dict], per_doc: int = 1) -> list[dict]:
    """Câu hỏi về bài A + nguồn là chunk của bài B (B không nhắc tên A)."""
    out: list[dict] = []
    for doc in docs:
        others = [d for d in docs if d["name"] != doc["name"]]
        rng.shuffle(others)
        picked = 0
        for other in others:
            if picked >= per_doc:
                break
            chunk = rng.choice(other["chunks"])
            # nguồn có nhắc tên di sản được hỏi thì không còn là distractor sạch:
            # lúc đó nguồn CÓ THỂ trả lời được, dạy từ chối là dạy sai.
            if contains_name(strip_accents(chunk["text"]), doc["name"]):
                continue
            out.append({"messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_msg(
                    chunk["text"], rng.choice(WRONG_DOC_QUESTIONS).format(name=doc["name"]))},
                {"role": "assistant", "content": rng.choice(WRONG_DOC_ANSWERS).format(
                    name=doc["name"], other=other["name"])},
            ]})
            picked += 1
    return out


# --- NER --------------------------------------------------------------------

NER_MIN_LABELS = 3      # câu ít hơn 3 entity thì mẫu quá dễ, không dạy được gì
NER_PER_DOC = 4
NER_SENT_CHARS = (60, 400)


def make_ner_samples(rng: random.Random, docs: list[dict], per_doc: int = NER_PER_DOC) -> list[dict]:
    """Mẫu NER với nhãn vàng lấy từ chính graph deterministic (backend/core/nerlabel.py).

    Nguồn được chọn NGẪU NHIÊN giữa "(không có)" và một chunk của bài KHÁC: đoạn
    cần trích nằm trong câu hỏi, nên model phải học rằng lệnh trích entity thắng
    phần `Nguồn:` dù phần đó rỗng hay không liên quan. Không có mẫu nào như vậy
    thì lúc serve, retrieval trả về context rỗng và model sẽ đi từ chối thay vì
    trích entity - đúng câu demo trong docs/demo-guide.md.
    """
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
        # ưu tiên câu phủ NHIỀU LOẠI entity nhất; 4 loại mà chỉ dạy 1 loại thì
        # macro-F1 của các loại còn lại đo trên tập rỗng, không có ý nghĩa.
        rng.shuffle(cands)
        cands.sort(key=lambda t: -t[0])
        picked = cands[:per_doc]

        # "sự kiện" chỉ có 2 tên trong cả corpus (Festival Huế, lễ hội Nguyễn Huệ)
        # nằm trong 7 câu. Xếp hạng theo SỐ LOẠI ở trên gần như luôn bỏ qua chúng,
        # và loại nào không có mẫu nào thì lúc eval F1 của nó đo trên tập rỗng -
        # vô nghĩa. Vì vậy mỗi loại được bảo đảm ít nhất một câu, nhận cả câu chỉ
        # có 2 nhãn nếu không còn câu nào khá hơn.
        for t in NER_TYPES:
            if any(lab[t] for _, _, lab in picked):
                continue
            extra = next((c for c in cands + weak if c[2][t]), None)
            if extra:
                picked.append(extra)

        others = [d for d in docs if d["name"] != doc["name"]] or docs
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


# --- Teacher LLM (tùy chọn) -------------------------------------------------

# Teacher chỉ VIẾT LẠI các câu đã chọn cho mượt, KHÔNG tự do trả lời: nếu để nó
# trả lời tự do thì nó bịa năm, bịa tên vua, và cái bịa đó vào thẳng training
# data - tức là dùng LLM để dạy model bịa. Trích dẫn do script tự ghép nên định
# dạng [Nguồn: ...] luôn đúng và luôn là chuỗi có thật trong nguồn.
TEACHER_SYSTEM = """Bạn là biên tập viên sách văn hóa. Việc của bạn là viết lại các câu tư liệu thành một đoạn văn liền mạch, giọng kể trang trọng và tự nhiên.
TUYỆT ĐỐI KHÔNG thêm bất kỳ thông tin, con số, năm, tên người hay tên địa danh nào không có trong tư liệu.
Không thêm lời chào, không thêm nhận xét của bạn, không trích nguồn, không gạch đầu dòng.
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
    """Generate through an OpenAI-compatible llama.cpp server."""
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
    """Trả về "" nếu câu trả lời chỉ dùng thông tin có trong nguồn, ngược lại lý do.

    Cổng cũ chỉ kiểm `len >= 120` và có chữ "[Nguồn:" - không hề chặn việc teacher
    bịa. Ba phép kiểm ở đây bắt đúng ba kiểu bịa hay gặp nhất: thêm số/năm, thêm
    tên riêng, và trả lời bằng một câu từ chối.
    """
    if len(answer) < 120:
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
    """Nhờ teacher viết lại `sents` cho mượt. Không qua cổng trung thực thì trả None."""
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


# --- Sinh mẫu ---------------------------------------------------------------

def pick_chunk(chunks: list[dict], used: set[int], intent: dict) -> tuple[int, dict] | None:
    """Chọn chunk LIÊN QUAN NHẤT tới câu hỏi; không có chunk đạt ngưỡng thì bỏ.

    Ưu tiên chunk chưa dùng, nhưng cho phép dùng lại: cùng một đoạn nguồn với
    hai câu hỏi khác nhau phải cho hai câu trả lời khác nhau - đó chính là tín
    hiệu dạy model đọc câu hỏi thay vì copy đầu đoạn.
    """
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

        # Teacher chỉ viết lại phần THÂN BÀI; trích dẫn do script ghép để định dạng
        # luôn đúng và câu trích luôn là chuỗi có thật trong chunk.
        body = teacher_rewrite(teacher, doc["name"], question, sents, stats) if teacher else None
        if body:
            quote = make_quote(chunk, sents, intent["kw"])
            answer = f"{body} [Nguồn: {quote} — {doc['url']}]"
        else:
            answer = build_answer(doc["name"], intent, chunk, doc["url"], rng, sents)
        if answer is None:
            skipped.append(intent["id"])
            continue

        samples.append({"messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_msg(chunk["text"], question)},
            {"role": "assistant", "content": answer},
        ]})
    return samples, skipped


def split_docs(docs: list[dict]) -> tuple[list[dict], list[dict]]:
    """Chia theo địa điểm: valid không dùng chung tài liệu với train."""
    valid = [d for i, d in enumerate(docs) if i % VALID_EVERY == 2]
    valid_names = {d["name"] for d in valid}
    train = [d for d in docs if d["name"] not in valid_names]
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
        "NER": make_ner_samples(rng, docs),
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


def dedupe(rows: list[dict]) -> list[dict]:
    """Bỏ mẫu trùng hoàn toàn (cùng câu hỏi + cùng câu trả lời)."""
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
    """Bỏ mẫu valid dùng đoạn nguồn đã xuất hiện trong train.

    "(không có)" là placeholder của mẫu refusal, không phải nguồn thật.
    """
    train_sources = {source_of(r) for r in train_rows}
    return [r for r in valid_rows
            if source_of(r) == "Nguồn: (không có)" or source_of(r) not in train_sources]




def count_refusals(rows: list[dict]) -> int:
    markers = ("Rất tiếc", "không đề cập", "không tìm thấy", "không thấy nội dung",
               "không chứa thông tin", "xin phép không suy đoán", "xin phép không trả lời",
               "xin dừng ở đây", "không có nội dung nào")
    return sum(1 for r in rows if any(m in r["messages"][-1]["content"] for m in markers))


def count_ner(rows: list[dict]) -> int:
    return sum(1 for r in rows if r["messages"][1]["content"].count(NER_QUESTION[:20]))


def ner_type_coverage(rows: list[dict]) -> dict[str, int]:
    """Mỗi loại entity được dạy trên bao nhiêu mẫu.

    Loại nào ~0 thì macro-F1 của nó về sau đo trên tập rỗng: ner_f1() trả 1.0 khi
    cả pred và gold đều rỗng, nên macro-F1 bị ĐẨY LÊN một cách giả tạo.
    """
    cover = {t: 0 for t in NER_TYPES}
    for row in rows:
        if not row["messages"][1]["content"].count(NER_QUESTION[:20]):
            continue
        try:
            label = json.loads(row["messages"][-1]["content"])
        except json.JSONDecodeError:
            continue
        for t in NER_TYPES:
            if label.get(t):
                cover[t] += 1
    return cover


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--use-model", action="store_true",
                        help="dùng LLM local sinh câu trả lời thay cho template")
    parser.add_argument("--model", default=DEFAULT_TEACHER,
                        help=f"URL llama.cpp teacher khi --use-model (mặc định: {DEFAULT_TEACHER})")
    args = parser.parse_args()

    if not INDEX_FILE.exists():
        print(f"ERROR: chưa có {INDEX_FILE}. Chạy ingestion/crawl_by_location.py trước.")
        sys.exit(1)

    rng = random.Random(SEED)
    docs, skipped_docs = load_docs()
    if not docs:
        print("ERROR: không có tài liệu nào dùng được.")
        sys.exit(1)

    print(f"=== Corpus: {len(docs)} tài liệu dùng được, {len(skipped_docs)} bị bỏ ===")
    for name, reason in skipped_docs:
        print(f"  - bỏ {name}: {reason}")

    teacher = args.model if args.use_model else None
    if teacher:
        print(f"\n=== Teacher: {teacher} (chỉ viết lại, có cổng trung thực) ===")
    else:
        print("\n=== Dùng template (thêm --use-model để nhờ LLM viết lại cho mượt) ===")

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
        ref, ner = count_refusals(rows), count_ner(rows)
        print(f"  {label}: {len(rows):>3} mẫu | {ref} refusal ({ref / len(rows):.0%}) | "
              f"{ner} NER ({ner / len(rows):.0%})  → {path}")
        print(f"         NER phủ theo loại: {ner_type_coverage(rows)}")
    print(f"\n  Gợi ý iters cho lora_config.yaml (batch_size 2, ~10 epoch): "
          f"{max(len(train_rows) * 10 // 2, 200)}")


if __name__ == "__main__":
    main()
