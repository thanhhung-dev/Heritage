#!/usr/bin/env python3
"""Sinh mẫu train cho CÂU KIỂM CHỨNG - "X ở Đà Nẵng đúng không?".

VẤN ĐỀ. Hỏi "Chùa Thiên Mụ ở Đà Nẵng đúng không", model trả lời "một địa điểm
nổi tiếng ở Đàng Trong... di sản văn hóa quý giá của địa phương" - né tiền đề
sai bằng cách nói vòng. Trong 305 mẫu của data/train_v3.jsonl KHÔNG có mẫu nào
dạng phản biện, model chưa từng thấy hình dạng "bác bỏ trước, kể sau".

SINH DETERMINISTIC, KHÔNG NHỜ LLM. Câu hỏi đúng/sai được suy từ metadata
(`region`, `category` trong locations_index.json) nên đáp án biết chắc. Nhờ
teacher đặt loại câu này là để nó bịa ground truth mà không có cách phát hiện.

BA RÀNG BUỘC, phá cái nào cũng đủ làm hỏng kết quả:

1. NGUỒN PHẢI CHỨA BẰNG CHỨNG. Mẫu nào có đáp án khẳng định "Huế" mà đoạn nguồn
   không chứa chữ "Huế" thì BỎ MẪU, không sửa đáp án. Để lại là dạy model trả
   lời bằng ký ức tham số - tức là dạy nó bịa, đúng bệnh đang cần chữa.
2. CÂN BẰNG ĐÚNG/SAI ~50/50. Lệch về "không đúng" thì model học phản đối mọi
   thứ, kể cả câu đúng. Script tự cân và in ra tỉ lệ.
3. ĐỊNH DẠNG GIỐNG HỆT 305 mẫu cũ: phán quyết -> đính chính -> [Nguồn: ...].
   Đổi hình dạng đáp án là làm loãng thứ adapter đã học tốt.

KHÔNG SAO NGUYÊN VĂN. Thân bài sinh 100% từ template + metadata, không lấy câu
nào từ nguồn. Bản đầu của script này có thêm 1-2 câu "kể tiếp" copy từ nguồn:
audit đo ra 130/130 mẫu vượt ngưỡng 14 từ, trung vị 57 từ liên tiếp trùng nguồn -
đúng lỗi mà bootstrap_v3.py được viết ra để chống. Phần verbatim duy nhất được
phép là trích dẫn trong [Nguồn: ...], như mọi mẫu khác.

Nguồn lấy qua ĐÚNG retrieval lúc serve (apps/backend/core/rag.retrieve_context), không
tự chọn chunk: mẫu train phải có `Nguồn:` cùng hình dạng với lúc chạy thật.

  # sinh + xem báo cáo
  apps/backend/.venv/bin/python pipelines/training/bootstrap_verify.py

  # trộn vào data/train_v3.jsonl và data/valid_v3.jsonl
  apps/backend/.venv/bin/python pipelines/training/bootstrap_verify.py --merge
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.backend.core.corpus import load_docs  # noqa: E402
from apps.backend.core.kg import extract_names, is_admin_name  # noqa: E402
from apps.backend.core.prompt import SYSTEM, user_msg  # noqa: E402
from apps.backend.core.rag import retrieve_context  # noqa: E402
from apps.backend.core.textutil import sentences, strip_accents  # noqa: E402
from pipelines.training.bootstrap_deep_qa import SEED, split_docs  # noqa: E402
from pipelines.training.bootstrap_v3 import (  # noqa: E402
    OUT_TRAIN,
    OUT_VALID,
    read_jsonl,
    write_jsonl,
)

OUT_VERIFY_TRAIN = ROOT / "data" / "verify_train.jsonl"
OUT_VERIFY_VALID = ROOT / "data" / "verify_valid.jsonl"

# Tỉ lệ tối đa mà mẫu kiểm chứng được chiếm trong tập train. Sinh hết cặp
# đúng/sai cho 45 bài ra 130 mẫu = 30% tập - quá nhiều cho MỘT khuôn câu trả lời
# rất cứng, model sẽ bắt đầu chào "Vâng, đúng vậy." cả với câu hỏi thường. 18%
# đủ để dạy hình dạng mà không lấn văn phong kể chuyện của 305 mẫu cũ.
#
# NÂNG 0.18 -> 0.24 khi thêm họ thứ tư (phủ định). Ngân sách cũ chia cho 4 họ là
# ~16 mẫu/họ, tức 8 khẳng định + 8 phản biện - quá mỏng để dạy một hình dạng mới,
# nhất là họ phủ định vốn khó hơn (model phải hiểu vế phủ định trước khi phán
# quyết). 0.24 cho ~22 mẫu/họ, bằng mức mà họ địa danh đã đo được là đủ. Đánh đổi
# là khuôn kiểm chứng chiếm chỗ của văn phong kể chuyện; theo dõi bằng chính bảng
# thành phần mà make_train_set.py in ra.
MAX_SHARE = 0.24

REGIONS = ("Huế", "Đà Nẵng")

# Nhãn category -> cách gọi trong câu hỏi tiếng Việt tự nhiên.
CATEGORY_PHRASE = {
    "Ẩm thực": "một món ăn",
    "Di tích lịch sử": "một di tích lịch sử",
    "Danh thắng": "một danh thắng",
    "Lễ hội": "một lễ hội",
    "Nghệ thuật": "một loại hình nghệ thuật",
    "Làng nghề": "một làng nghề",
}

# --- Mẫu câu hỏi -------------------------------------------------------------
# Đa dạng cách hỏi nhưng KHÔNG đa dạng cách trả lời: hình dạng đáp án phải cố
# định để adapter học được một khuôn duy nhất.
#
# CÓ CẢ KHẨU NGỮ. Bốn khuôn đầu là văn viết; người chat gõ "hả?", "à?", "nhỉ?".
# Đo được: "Lăng Tự Đức ở phường hoà hải hả?" bị model XÁC NHẬN một điều sai dù
# nguồn ghi rõ "phường Thủy Xuân" - trong khi cùng câu với "đúng không?" thì bác
# đúng. Adapter học hình dạng câu, nên hình dạng nào không có trong tập train thì
# nó rơi về hành vi mặc định của base là đồng ý với người hỏi.
QUESTION_TAILS = (
    "đúng không?", "phải không?", "đúng chứ?",
    "hả?", "à?", "nhỉ?", "ha?", "đúng chớ?",
)
REGION_QUESTIONS = (
    "{name} ở {region} đúng không?",
    "{name} có phải ở {region} không?",
    "{name} nằm ở {region} phải không?",
    "Nghe nói {name} ở {region}, đúng chứ?",
    "{name} ở {region} hả?",
    "{name} ở {region} à?",
    "{name} thuộc {region} nhỉ?",
    "{name} ở {region} ha?",
)
CATEGORY_QUESTIONS = (
    "{name} là {phrase} đúng không?",
    "{name} có phải là {phrase} không?",
    "{name} là {phrase} hả?",
    "{name} là {phrase} à?",
)
# Câu hỏi CẤP HÀNH CHÍNH. Cùng bộ đuôi nghi vấn để khuôn khẩu ngữ phủ cả hai họ
# mẫu - lỗi đo được xảy ra ở đúng giao điểm "cấp phường" x "khẩu ngữ".
ADMIN_QUESTIONS = (
    "{name} ở {unit} {tail}",
    "{name} thuộc {unit} {tail}",
    "{name} nằm ở {unit} {tail}",
)

# Câu hỏi PHỦ ĐỊNH - giả định nằm trong một vế PHỦ ĐỊNH ("X không ở Huế đúng
# không?"). Đo được đây là họ hỏng nặng nhất: 3/3 ca sai, và sai theo cách tệ hơn
# hai họ kia. Model đọc "Đúng vậy" là đồng ý với vế phủ định rồi TỰ SINH một vế
# thay thế không có trong nguồn:
#   Q: Lăng Tự Đức không ở Huế đúng không?   (nguồn: "phường Thủy Xuân, Huế")
#   A: Đúng vậy. Lăng Tự Đức không thuộc Huế mà thuộc Đà Nẵng.
# Tức là không chỉ xác nhận sai mà còn bịa ra địa danh mới. Tập cũ có 0 mẫu dạng này.
NEGATIVE_REGION_QUESTIONS = (
    "{name} không ở {region} {tail}",
    "{name} không thuộc {region} {tail}",
    "{name} không nằm ở {region} {tail}",
)
NEGATIVE_ADMIN_QUESTIONS = (
    "{name} không ở {unit} {tail}",
    "{name} không thuộc {unit} {tail}",
)

# --- Mẫu đáp án --------------------------------------------------------------
# Phán quyết đứng ĐẦU: đó là thứ người hỏi cần, và là hình dạng model phải học.
# Toàn bộ thân bài ghép từ template + metadata, KHÔNG lấy câu nào từ nguồn -
# xem phần "KHÔNG SAO NGUYÊN VĂN" ở docstring module.
YES_LEAD = (
    "Vâng, đúng vậy.",
    "Đúng vậy.",
    "Chính xác.",
)
NO_LEAD = (
    "Thưa bạn, thông tin này chưa chính xác.",
    "Không phải vậy ạ.",
    "Xin phép được đính chính:",
)

REGION_YES = "{name} thuộc {region}."
REGION_NO = "{name} không thuộc {region} mà thuộc {truth}."
CATEGORY_YES = "{name} đúng là {phrase} của {region}."
CATEGORY_NO = "{name} không phải {wrong} mà là {truth} của {region}."
# Cấp hành chính: đáp án nêu ĐỦ cả địa danh nhỏ và vùng, vì người hỏi ở cấp phường
# thường không biết phường đó thuộc tỉnh nào - trả lời "không thuộc phường X" mà
# không nói thuộc đâu thì đính chính xong vẫn để người hỏi tay trắng.
ADMIN_YES = "{name} thuộc {unit}, {region}."
ADMIN_NO = "{name} không thuộc {unit} mà thuộc {truth}, {region}."

# PHỦ ĐỊNH. Hai điều bắt buộc, thiếu cái nào cũng làm mẫu trở nên vô dụng:
#
# 1. Phán quyết trả lời VẾ PHỦ ĐỊNH, không trả lời tên vùng. Câu "X không ở Huế
#    đúng không?" mà X ở Huế thật thì vế phủ định SAI -> phải mở đầu bằng NO_LEAD.
#    Đây là chỗ dễ lẫn nhất: cùng một tên vùng ĐÚNG lại cho phán quyết ngược so
#    với họ region.
# 2. Câu tiếp theo phải nêu SỰ THẬT ở dạng KHẲNG ĐỊNH ("X có ở Huế"), không lặp
#    lại vế phủ định. Lặp lại là dạy model dùng câu hai phủ định mà chính nó đang
#    hiểu sai.
NEGATIVE_WRONG = "{name} có ở {truth}."          # vế phủ định SAI -> đính chính
NEGATIVE_RIGHT = "{name} thật sự không ở {claim} mà ở {truth}."   # vế phủ định ĐÚNG

# Câu kết, cũng thuần template. Có mặt để đáp án không cụt lủn một dòng - văn
# phong "giàu tính kể chuyện" mà SYSTEM đòi - nhưng không thêm dữ kiện nào.
REGION_TAIL = (
    "Đây là một trong những di sản tiêu biểu của {truth}.",
    "Bạn có thể tìm đến {truth} nếu muốn tham quan.",
    "Xin bạn lưu ý điều này khi tìm hiểu về {truth}.",
)


def _evidence_sentence(source: str, needle: str, subject: str = "") -> str:
    """Câu trong nguồn có chứa `needle` - dùng làm trích dẫn.

    Trả về "" nếu không có: khi đó mẫu bị BỎ. Đây là cổng thực thi ràng buộc 1.

    ƯU TIÊN CÂU CHỨA CẢ `subject`. Chỉ tìm câu đầu tiên chứa tên vùng thì bài "Bánh
    khoái" nhận trích dẫn "Người Huế phát âm từ khói tựa như khoái" - có chữ Huế
    nhưng không chứng minh bánh khoái là món Huế, trong khi cùng nguồn có câu "Bánh
    khoái chỉ có ở Huế và rất khó làm...". Đo được 6/45 bài cải thiện nhờ bước này.
    Vẫn có nhánh dự phòng vì 3 bài (Làng Non Nước, Làng Thanh Hà, Lăng Khải Định)
    dùng chủ ngữ rút gọn nên không có câu nào chứa cả hai.
    """
    plain_needle = strip_accents(needle)
    plain_subject = strip_accents(subject) if subject else ""
    fallback = ""
    for sent in sentences(source):
        plain = strip_accents(sent)
        if plain_needle not in plain:
            continue
        if plain_subject and plain_subject in plain:
            return sent
        fallback = fallback or sent
    return fallback


def _make_sample(question: str, source: str, answer_body: str, quote: str,
                 url: str) -> dict:
    return {"messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_msg(source, question)},
        {"role": "assistant", "content": f"{answer_body} [Nguồn: {quote} — {url}]"},
    ]}


def _tail(rng: random.Random, truth: str) -> str:
    """Câu kết thuần template.

    Bản đầu lấy 1-2 câu từ nguồn ở đây và audit đo ra 130/130 mẫu copy nguyên
    văn (trung vị 57 từ liên tiếp). Câu kết không mang dữ kiện nên không cần
    nguồn - ghép từ template là đủ và không dạy model photocopy.
    """
    return rng.choice(REGION_TAIL).format(truth=truth)


ADMIN_UNITS = ("phường", "xã")

# Động từ định vị: dấu hiệu câu đang ghi ĐỊA CHỈ chứ không kể chuyện.
LOC_VERB_RE = re.compile(
    r"\b(toa lac|nam o|nam tren|nam ben|nam dua|thuoc|dia chi|nay la|nay thuoc"
    r"|hien nay)\b"
)

NOT_ADDRESS_RE = re.compile(
    r"\b(xua thuoc|xua la|truoc day|truoc kia|doi ten|chep|sach|bat nguon"
    r"|chay qua|chay tu|hop luu|nga ba|phan luu|chi luu)\b"
)


def admin_units_of(doc: dict) -> list[str]:
    """Địa danh cấp phường/xã trong CÂU ĐỊA CHỈ của bài; [] nếu không có.

    Câu địa chỉ phải thoả ba điều, thiếu một là bỏ:
      1. có ĐÚNG MỘT địa danh cấp phường/xã. Nhiều hơn thì địa chỉ không duy nhất
         ("đầu cầu phía bắc thuộc phường Phú Xuân; phía nam thuộc phường Thuận
         Hóa") - Cầu Trường Tiền thật sự nằm giữa hai phường, không có đáp án đúng.
      2. KHÔNG mang dấu hiệu địa danh cổ / dòng chảy (NOT_ADDRESS_RE).
      3. nhắc tên bài, HOẶC có động từ định vị + tên vùng của bài. Nhánh sau cần vì
         wiki hay viết "Lăng tọa lạc tại núi Châu Chữ, phường Thủy Xuân, thành phố
         Huế" - chủ ngữ rút gọn thành "Lăng", không nhắc lại tên đầy đủ. Chỉ đòi
         nhắc tên bài thì mất 6 bài (9 -> 15 khi thêm nhánh này).
    """
    source, _hits = retrieve_context(f"{doc['name']} ở phường nào?")
    if not source:
        return []
    plain_doc = strip_accents(doc["name"])
    plain_region = strip_accents(doc["region"])
    for sent in sentences(source):
        plain = strip_accents(sent)
        units = [n for n in extract_names(sent)
                 if is_admin_name(n) and n.split()[0] in ADMIN_UNITS]
        if len(units) != 1 or NOT_ADDRESS_RE.search(plain):
            continue
        if plain_doc in plain or (LOC_VERB_RE.search(plain) and plain_region in plain):
            return units
    return []


def admin_wrong_pool(docs: list[dict]) -> dict[str, list[str]]:
    """{vùng: [địa danh của vùng KHÁC]} - dùng làm giả định SAI.

    Địa danh sai phải KHÁC VÙNG với bài đang sinh mẫu: corpus có 3 bài cùng ở
    "phường Thủy Xuân" (Lăng Tự Đức, Lăng Khải Định, Chùa Từ Hiếu), nên lấy địa
    danh cùng vùng làm "đáp án sai" là sinh ra mẫu sai sự thật.
    """
    by_region: dict[str, set[str]] = {}
    for doc in docs:
        for unit in doc.get("admin_units") or []:
            by_region.setdefault(doc["region"], set()).add(unit)
    return {
        region: sorted(u for other, units in by_region.items() if other != region
                       for u in units)
        for region in by_region
    }


def region_samples(doc: dict, rng: random.Random, stats: Counter) -> list[dict]:
    """Cặp (ĐÚNG, SAI) về vùng cho một bài. Bỏ cả cặp nếu thiếu bằng chứng."""
    truth = doc["region"]
    wrong = next(r for r in REGIONS if r != truth)
    out: list[dict] = []

    for region, is_true in ((truth, True), (wrong, False)):
        question = rng.choice(REGION_QUESTIONS).format(name=doc["name"], region=region)
        source, _hits = retrieve_context(question)
        if not source:
            stats["bỏ: retrieval không trả nguồn"] += 1
            continue
        quote = _evidence_sentence(source, truth, doc["name"])
        if not quote:
            stats["bỏ: nguồn không có bằng chứng vùng"] += 1
            continue
        if is_true:
            body = f"{rng.choice(YES_LEAD)} {REGION_YES.format(name=doc['name'], region=truth)}"
        else:
            body = (f"{rng.choice(NO_LEAD)} "
                    f"{REGION_NO.format(name=doc['name'], region=region, truth=truth)}")
        body = f"{body} {_tail(rng, truth)}"
        out.append(_make_sample(question, source, body, quote, doc["url"]))
        stats["nhận: vùng ĐÚNG" if is_true else "nhận: vùng SAI"] += 1
    return out


def category_samples(doc: dict, rng: random.Random, stats: Counter) -> list[dict]:
    """Cặp (ĐÚNG, SAI) về loại. Bằng chứng là câu định nghĩa của wiki."""
    truth = doc["category"]
    if truth not in CATEGORY_PHRASE:
        return []
    wrong = next(c for c in CATEGORY_PHRASE if c != truth)
    out: list[dict] = []

    for category, is_true in ((truth, True), (wrong, False)):
        phrase = CATEGORY_PHRASE[category]
        question = rng.choice(CATEGORY_QUESTIONS).format(name=doc["name"], phrase=phrase)
        source, _hits = retrieve_context(question)
        if not source:
            stats["bỏ: retrieval không trả nguồn"] += 1
            continue
        # Bằng chứng loại: câu nào trong nguồn nhắc chính tên bài - câu định nghĩa
        # của wiki ("Mì Quảng là một loại mì ở Đà Nẵng...") gần như luôn là câu đó.
        quote = _evidence_sentence(source, doc["name"])
        if not quote:
            stats["bỏ: nguồn không có câu định nghĩa"] += 1
            continue
        if is_true:
            body = (f"{rng.choice(YES_LEAD)} "
                    f"{CATEGORY_YES.format(name=doc['name'], phrase=phrase, region=doc['region'])}")
        else:
            body = (f"{rng.choice(NO_LEAD)} "
                    f"{CATEGORY_NO.format(name=doc['name'], wrong=phrase, truth=CATEGORY_PHRASE[truth], region=doc['region'])}")
        body = f"{body} {_tail(rng, doc['region'])}"
        out.append(_make_sample(question, source, body, quote, doc["url"]))
        stats["nhận: loại ĐÚNG" if is_true else "nhận: loại SAI"] += 1
    return out


def admin_samples(doc: dict, rng: random.Random, stats: Counter,
                  wrong_pool: dict[str, list[str]]) -> list[dict]:
    """Cặp (ĐÚNG, SAI) về ĐỊA DANH HÀNH CHÍNH (phường/xã/quận/huyện).

    LẤY ĐỊA DANH TỪ CÂU ĐỊNH NGHĨA, không lấy từ cả đoạn nguồn. Bài "Sông Hàn"
    nhắc 10 địa danh vì nó kể dòng chảy qua nhiều nơi, "Lễ Cầu ngư" nhắc "phường
    Quy Nhơn Đông" vì liệt kê các tỉnh có lễ này. Lấy bất kỳ địa danh nào trong
    nguồn là dạy model gán địa chỉ sai - tệ hơn hẳn so với không có mẫu.

    ĐỊA DANH SAI lấy từ bài KHÁC trong corpus (`wrong_pool`), không bịa tên: tên
    bịa không có trong KG nên câu hỏi tương ứng sẽ bị cổng REQUIRE_KNOWN_ADMIN của
    rag.py từ chối lúc serve - mẫu train khi đó dạy một tình huống không bao giờ
    xảy ra. Và phải khác VÙNG với bài này, nếu không "phường Thủy Xuân" (Lăng Tự
    Đức) lại làm đáp án sai cho "Lăng Khải Định" - hai lăng thật sự cùng phường.
    """
    truths = doc.get("admin_units") or []
    if not truths:
        return []
    truth = truths[0]
    pool = wrong_pool.get(doc["region"], [])
    if not pool:
        stats["bỏ: không có địa danh sai cùng cấp"] += 1
        return []
    wrong = rng.choice(pool)
    out: list[dict] = []

    for unit, is_true in ((truth, True), (wrong, False)):
        tail = rng.choice(QUESTION_TAILS)
        question = rng.choice(ADMIN_QUESTIONS).format(
            name=doc["name"], unit=unit, tail=tail)
        source, _hits = retrieve_context(question)
        if not source:
            stats["bỏ: retrieval không trả nguồn"] += 1
            continue
        # Bằng chứng luôn là địa danh THẬT, kể cả với câu hỏi sai: muốn bác "ở
        # phường Hòa Hải" thì nguồn phải chứng minh được "ở phường Thủy Xuân".
        quote = _evidence_sentence(source, truth, doc["name"])
        if not quote:
            stats["bỏ: nguồn không có bằng chứng địa danh"] += 1
            continue
        if is_true:
            body = (f"{rng.choice(YES_LEAD)} "
                    f"{ADMIN_YES.format(name=doc['name'], unit=truth, region=doc['region'])}")
        else:
            body = (f"{rng.choice(NO_LEAD)} "
                    f"{ADMIN_NO.format(name=doc['name'], unit=unit, truth=truth, region=doc['region'])}")
        body = f"{body} {_tail(rng, doc['region'])}"
        out.append(_make_sample(question, source, body, quote, doc["url"]))
        stats["nhận: địa danh ĐÚNG" if is_true else "nhận: địa danh SAI"] += 1
    return out


def negative_samples(doc: dict, rng: random.Random, stats: Counter,
                     wrong_pool: dict[str, list[str]]) -> list[dict]:
    """Cặp mẫu PHỦ ĐỊNH: một câu có vế phủ định SAI, một câu có vế phủ định ĐÚNG.

    Đây là họ mà model hiện tại sai 3/3 - và sai theo cách nặng nhất: nó xác nhận
    vế phủ định rồi TỰ SINH một vùng thay thế không có trong nguồn.

    CÂN BẰNG LÀ BẮT BUỘC Ở ĐÂY, không phải tuỳ chọn. Chỉ dạy "vế phủ định thường
    sai" thì model học phản đối mọi câu có chữ "không", tức là đổi một lỗi hệ thống
    thành một lỗi hệ thống khác. Nên mỗi bài sinh đúng hai mẫu:
      - "X không ở {vùng thật}"  -> vế phủ định SAI  -> NO_LEAD, đính chính
      - "X không ở {vùng khác}"  -> vế phủ định ĐÚNG -> YES_LEAD, xác nhận
    Cả hai đều dùng CÙNG một câu bằng chứng (vùng thật), nên cùng đòi hỏi model
    đọc nguồn chứ không đọc hình dạng câu.
    """
    truth = doc["region"]
    other = next(r for r in REGIONS if r != truth)
    out: list[dict] = []

    # (vùng bị phủ định, vế phủ định có ĐÚNG không)
    for claim, negation_true in ((truth, False), (other, True)):
        tail = rng.choice(QUESTION_TAILS)
        question = rng.choice(NEGATIVE_REGION_QUESTIONS).format(
            name=doc["name"], region=claim, tail=tail)
        source, _hits = retrieve_context(question)
        if not source:
            stats["bỏ: retrieval không trả nguồn"] += 1
            continue
        quote = _evidence_sentence(source, truth, doc["name"])
        if not quote:
            stats["bỏ: nguồn không có bằng chứng vùng"] += 1
            continue
        if negation_true:
            body = (f"{rng.choice(YES_LEAD)} "
                    f"{NEGATIVE_RIGHT.format(name=doc['name'], claim=claim, truth=truth)}")
        else:
            body = (f"{rng.choice(NO_LEAD)} "
                    f"{NEGATIVE_WRONG.format(name=doc['name'], truth=truth)}")
        body = f"{body} {_tail(rng, truth)}"
        out.append(_make_sample(question, source, body, quote, doc["url"]))
        stats["nhận: phủ định ĐÚNG" if negation_true else "nhận: phủ định SAI"] += 1

    # Thêm một cặp ở CẤP PHƯỜNG khi bài có địa chỉ - giao điểm "phủ định x cấp
    # phường" là chỗ hai họ hỏng gặp nhau, và nó không tự suy ra từ hai họ riêng lẻ.
    units = doc.get("admin_units") or []
    pool = wrong_pool.get(doc["region"], [])
    if units and pool:
        unit_truth = units[0]
        for claim, negation_true in ((unit_truth, False), (rng.choice(pool), True)):
            tail = rng.choice(QUESTION_TAILS)
            question = rng.choice(NEGATIVE_ADMIN_QUESTIONS).format(
                name=doc["name"], unit=claim, tail=tail)
            source, _hits = retrieve_context(question)
            if not source:
                stats["bỏ: retrieval không trả nguồn"] += 1
                continue
            quote = _evidence_sentence(source, unit_truth, doc["name"])
            if not quote:
                stats["bỏ: nguồn không có bằng chứng địa danh"] += 1
                continue
            if negation_true:
                body = (f"{rng.choice(YES_LEAD)} "
                        f"{NEGATIVE_RIGHT.format(name=doc['name'], claim=claim, truth=unit_truth)}")
            else:
                body = (f"{rng.choice(NO_LEAD)} "
                        f"{NEGATIVE_WRONG.format(name=doc['name'], truth=unit_truth)}")
            body = f"{body} {_tail(rng, doc['region'])}"
            out.append(_make_sample(question, source, body, quote, doc["url"]))
            stats["nhận: phủ định ĐÚNG" if negation_true else "nhận: phủ định SAI"] += 1
    return out


def build(docs: list[dict], rng: random.Random, stats: Counter) -> list[dict]:
    wrong_pool = admin_wrong_pool(docs)
    rows: list[dict] = []
    for doc in docs:
        rows.extend(region_samples(doc, rng, stats))
        rows.extend(category_samples(doc, rng, stats))
        rows.extend(admin_samples(doc, rng, stats, wrong_pool))
        rows.extend(negative_samples(doc, rng, stats, wrong_pool))
    return unaccent_some(rows, rng, stats)


# --- BIẾN THỂ KHÔNG DẤU ------------------------------------------------------
# 0/583 mẫu trong tập cũ là câu không dấu, dù pipelines/evaluation/eval_retrieval.py có 6 ca không
# dấu và apps/backend/core/textutil.py được viết riêng để xử lý chúng. Retrieval lo
# được ("lang tu duc o da nang dung khong" vẫn lấy đúng bài), nhưng LoRA chưa từng
# thấy hình dạng đó nên đo được 1/4 ca bị xác nhận sai.
#
# Chỉ bỏ dấu CÂU HỎI, giữ nguyên đáp án. Người gõ không dấu vẫn muốn đọc câu trả
# lời có dấu, nên bỏ dấu cả đáp án là dạy một hành vi không ai muốn.
#
# NHƯNG NGUỒN PHẢI LẤY LẠI. Câu không dấu đi qua retrieval cho ra đoạn nguồn KHÁC
# (đo được 6/18 mẫu lệch, chênh tới 481 ký tự) - giữ nguồn của câu có dấu là tạo ra
# đúng loại lệch train/serve mà module này được viết ra để chống. Nếu nguồn mới
# không còn chứa câu trích dẫn thì HOÀN NGUYÊN về câu có dấu, không bỏ mẫu: bỏ sẽ
# làm lệch cân bằng khẳng định/phản biện trong họ.
UNACCENT_SHARE = 0.15


def unaccent_some(rows: list[dict], rng: random.Random, stats: Counter) -> list[dict]:
    """Bỏ dấu câu hỏi của ~UNACCENT_SHARE mẫu, LẤY LẠI nguồn bằng câu không dấu."""
    n = int(len(rows) * UNACCENT_SHARE)
    if n <= 0:
        return rows
    for row in rng.sample(rows, n):
        question = row["messages"][1]["content"].rsplit("\n\nCâu hỏi: ", 1)[1]
        plain_q = strip_accents(question)
        source, _hits = retrieve_context(plain_q)
        quote = row["messages"][-1]["content"].split("[Nguồn:", 1)[1].rsplit("—", 1)[0].strip()
        if not source or quote not in source:
            stats["bỏ biến thể không dấu: nguồn mới thiếu trích dẫn"] += 1
            continue
        row["messages"][1]["content"] = user_msg(source, plain_q)
        stats["biến thể: câu hỏi không dấu"] += 1
    return rows


# --- Kiểm tra sau khi sinh ---------------------------------------------------

def is_refutation(row: dict) -> bool:
    answer = row["messages"][-1]["content"]
    return any(answer.startswith(lead) for lead in NO_LEAD)


def source_of(row: dict) -> str:
    head = row["messages"][1]["content"].split("\n\nCâu hỏi:")[0]
    return head[len("Nguồn: "):] if head.startswith("Nguồn: ") else head


def check_evidence(rows: list[dict]) -> list[str]:
    """Mọi câu trích dẫn PHẢI là chuỗi có thật trong đoạn nguồn của cùng mẫu.

    Đây là ràng buộc 1, kiểm lại một lần nữa sau khi sinh: cổng lúc sinh có thể
    bị sửa hỏng về sau mà không ai biết, còn báo cáo này thì đọc được bằng mắt.
    """
    bad: list[str] = []
    for i, row in enumerate(rows):
        answer = row["messages"][-1]["content"]
        if "[Nguồn:" not in answer:
            bad.append(f"mẫu {i}: thiếu [Nguồn: ...]")
            continue
        quote = answer.split("[Nguồn:", 1)[1].rsplit("—", 1)[0].strip()
        if quote not in source_of(row):
            bad.append(f"mẫu {i}: trích dẫn không có trong nguồn: {quote[:50]!r}")
    return bad


# Địa danh THẬT trong thân bài: sau "mà thuộc" (mẫu phản biện) hoặc sau "thuộc"
# (mẫu khẳng định). Cần để `check_admin_evidence` biết phải tìm gì trong trích dẫn.
TRUTH_AFTER_NO_RE = re.compile(r"mà thuộc ((?:phường|xã) [^,.]+)")
TRUTH_AFTER_YES_RE = re.compile(r"^[^.]+\.\s*[^.]*? thuộc ((?:phường|xã) [^,.]+)")


def check_admin_evidence(rows: list[dict]) -> list[str]:
    """Với mẫu ĐỊA DANH: trích dẫn phải chứa CHÍNH địa danh mà đáp án khẳng định.

    `check_evidence` chỉ kiểm trích dẫn có thật trong nguồn, không kiểm nó có
    CHỨNG MINH được điều đáp án nói. Mẫu "Lăng Tự Đức không thuộc phường Ngũ Hành
    Sơn mà thuộc phường Thủy Xuân" kèm một trích dẫn nói về kiến trúc thì vẫn qua
    cổng cũ - và nó dạy model đúng thứ đang phải chữa: kết luận không có bằng chứng.
    """
    bad: list[str] = []
    for i, row in enumerate(rows):
        if family_of(row) != "địa danh":
            continue
        answer = row["messages"][-1]["content"]
        body = answer.split("[Nguồn:")[0]
        quote = answer.split("[Nguồn:", 1)[1].rsplit("—", 1)[0]
        m = TRUTH_AFTER_NO_RE.search(body) or TRUTH_AFTER_YES_RE.search(body)
        if not m:
            bad.append(f"mẫu {i}: không đọc được địa danh trong đáp án: {body[:60]!r}")
            continue
        if strip_accents(m.group(1)) not in strip_accents(quote):
            bad.append(f"mẫu {i}: trích dẫn không chứng minh {m.group(1)!r}")
    return bad


# Hai khuôn đáp án của họ phủ định, dùng để đọc lại PHÁN QUYẾT từ chính câu trả lời.
# Phải bỏ câu lead trước khi khớp, nếu không group(1) ăn cả "Vâng, đúng vậy." và
# phép so tên với metadata luôn trượt.
LEAD_RE = re.compile(r"^(?:" + "|".join(re.escape(x) for x in YES_LEAD + NO_LEAD) + r")\s*")
NEG_WRONG_RE = re.compile(r"^(.+?) có ở ([^.]+)\.")
NEG_RIGHT_RE = re.compile(r"^(.+?) thật sự không ở (.+?) mà ở ([^.]+)\.")


def check_negative_truth(rows: list[dict], places: dict[str, set[str]]) -> list[str]:
    """Với mẫu PHỦ ĐỊNH: phán quyết phải KHỚP sự thật trong metadata.

    Đây là họ dễ sinh sai nhất vì phán quyết ĐẢO so với họ region: cùng tên vùng
    ĐÚNG, câu khẳng định cho YES_LEAD còn câu phủ định cho NO_LEAD. Lẫn một lần là
    24 mẫu dạy model ngược. Cổng này đọc lại phán quyết từ chính câu trả lời rồi so
    với `places` (vùng + phường thật của bài), nên không tin vào logic lúc sinh.
    """
    bad: list[str] = []
    for i, row in enumerate(rows):
        if family_of(row) != "phủ định":
            continue
        body = LEAD_RE.sub("", row["messages"][-1]["content"].split("[Nguồn:")[0].strip())
        refuted = is_refutation(row)
        m = NEG_WRONG_RE.match(body)
        if m:
            name, place = m.group(1), m.group(2)
            # "X có ở Y" -> vế phủ định trong câu hỏi SAI -> phải là mẫu đính chính
            if place not in places.get(name, set()) or not refuted:
                bad.append(f"mẫu {i}: {name!r} có ở {place!r} nhưng thật là "
                           f"{sorted(places.get(name, set()))}, refuted={refuted}")
            continue
        m = NEG_RIGHT_RE.match(body)
        if m:
            name, claim, said = m.group(1), m.group(2), m.group(3)
            # "X thật sự không ở A mà ở B" -> vế phủ định ĐÚNG -> phải là mẫu xác nhận
            known = places.get(name, set())
            if said not in known or claim in known or refuted:
                bad.append(f"mẫu {i}: {name!r} không ở {claim!r} mà ở {said!r}, "
                           f"thật là {sorted(known)}, refuted={refuted}")
            continue
        bad.append(f"mẫu {i}: không đọc được phán quyết phủ định: {body[:60]!r}")
    return bad


def balance_report(rows: list[dict], label: str) -> None:
    n_no = sum(1 for r in rows if is_refutation(r))
    n_yes = len(rows) - n_no
    pct = f"{n_no / len(rows):.0%}" if rows else "0%"
    fams = Counter(family_of(r) for r in rows)
    print(f"  {label}: {len(rows):>3} mẫu | {n_yes} khẳng định / {n_no} phản biện ({pct})"
          f" | {dict(fams)}")


# BỐN HỌ mẫu, phân biệt bằng THÂN BÀI của câu trả lời (thân bài do template sinh
# nên khuôn cố định). Dùng để chia ngân sách đều - xem `rebalance`.
#
# Phải bỏ phần [Nguồn: ...] trước khi so khớp: trích dẫn là câu nguyên văn của wiki
# và nó cũng chứa "thuộc phường X" ("Đầu cầu phía bắc thuộc phường Phú Xuân..."),
# nên so trên cả chuỗi thì 6/24 mẫu vùng bị đếm sang họ địa danh.
ADMIN_MARK = re.compile(r"\bthuộc (?:phường|xã) ")
# Họ PHỦ ĐỊNH nhận dạng bằng khuôn đáp án riêng của nó (NEGATIVE_WRONG /
# NEGATIVE_RIGHT), phải xét TRƯỚC ADMIN_MARK vì mẫu phủ định cấp phường cũng chứa
# "thuộc phường X" trong nhánh NEGATIVE_RIGHT.
NEGATIVE_MARK = re.compile(r"\b(có ở|thật sự không ở)\b")


def family_of(row: dict) -> str:
    answer = row["messages"][-1]["content"].split("[Nguồn:")[0]
    if NEGATIVE_MARK.search(answer):
        return "phủ định"
    if ADMIN_MARK.search(answer):
        return "địa danh"
    return "loại" if "là một" in answer or "phải một" in answer else "vùng"


def rebalance(rows: list[dict], rng: random.Random, cap: int | None = None) -> list[dict]:
    """Cân khẳng định/phản biện về ~50/50 TRONG TỪNG HỌ, và chia đều ngân sách.

    `cap` là số mẫu tối đa; cắt ĐỀU hai nhóm để tỉ lệ không lệch sau khi cắt.

    CHIA ĐỀU THEO HỌ, không cắt ngẫu nhiên trên cả pool. Pool sinh ra lệch theo
    lượng metadata có sẵn - 67 mẫu loại / 63 mẫu vùng / 22 mẫu địa danh - nên cắt
    ngẫu nhiên giữ nguyên tỉ lệ đó: 44% ngân sách rơi vào họ LOẠI (đo được model
    đã làm đúng) và 14% cho họ ĐỊA DANH (đúng họ đang sai). Kích thước pool phản
    ánh corpus có bao nhiêu bài ghi phường, không phản ánh họ nào cần dạy.

    Cân bằng yes/no phải làm TRONG từng họ: cân trên cả pool thì một họ có thể
    thành toàn phản biện, dạy model phản đối mọi câu hỏi cấp phường.
    """
    if cap is None:
        yes = [r for r in rows if not is_refutation(r)]
        no = [r for r in rows if is_refutation(r)]
        keep = min(len(yes), len(no))
        rng.shuffle(yes)
        rng.shuffle(no)
        out = yes[:keep] + no[:keep]
        rng.shuffle(out)
        return out

    by_family: dict[str, list[dict]] = {}
    for row in rows:
        by_family.setdefault(family_of(row), []).append(row)

    # Ngân sách chia đều, rồi phần dư của họ thiếu mẫu được trả lại cho họ khác.
    quota = {f: cap // max(len(by_family), 1) for f in by_family}
    out: list[dict] = []
    for _ in range(2):   # hai lượt: lượt hai tiêu phần dư của lượt một
        leftover = 0
        for fam, pool in by_family.items():
            yes = [r for r in pool if not is_refutation(r) and r not in out]
            no = [r for r in pool if is_refutation(r) and r not in out]
            keep = min(len(yes), len(no), max(quota[fam] // 2, 0))
            rng.shuffle(yes)
            rng.shuffle(no)
            out += yes[:keep] + no[:keep]
            leftover += quota[fam] - 2 * keep
        if leftover <= 0:
            break
        share = leftover // max(len(by_family), 1)
        quota = {f: share for f in by_family}
    rng.shuffle(out)
    return out


def sync_system(rows: list[dict]) -> int:
    """Ghi lại SYSTEM hiện tại vào mọi mẫu. Trả về số mẫu bị đổi.

    Thêm quy tắc đính chính vào SYSTEM (apps/backend/core/prompt.py) làm 305 mẫu cũ
    mang SYSTEM CŨ - model sẽ được train trên một prompt và serve bằng prompt
    khác, đúng loại lệch mà prompt.py được viết ra để chống. An toàn khi ghi đè:
    thân câu trả lời của mẫu cũ do template hoặc teacher (dùng TEACHER_SYSTEM
    riêng) sinh ra, không phụ thuộc SYSTEM.
    """
    changed = 0
    for row in rows:
        if row["messages"][0]["content"] != SYSTEM:
            row["messages"][0]["content"] = SYSTEM
            changed += 1
    return changed


def is_verify_sample(row: dict) -> bool:
    """Mẫu do CHÍNH script này sinh ra, nhận dạng bằng câu mở đầu cố định.

    Cần để `--merge` CHẠY LẠI ĐƯỢC. Bản trước chỉ `old + extra`, nên chạy hai lần
    là có hai bộ mẫu kiểm chứng trong tập train và MAX_SHARE bị vượt âm thầm - đúng
    thứ mà hằng số đó được đặt ra để chặn. Đo trên data hiện tại: 66/452 mẫu khớp,
    bằng đúng số mẫu đã trộn lần trước, nên phép nhận dạng này tin được.
    """
    answer = row["messages"][-1]["content"]
    return any(answer.startswith(lead) for lead in YES_LEAD + NO_LEAD)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", action="store_true",
                    help=f"trộn vào {OUT_TRAIN.name} / {OUT_VALID.name}")
    args = ap.parse_args()

    rng = random.Random(SEED)
    docs, _skipped = load_docs()
    # Địa danh hành chính đi qua retrieval thật nên tính MỘT lần rồi gắn vào doc,
    # thay vì gọi lại trong từng lần sinh mẫu.
    for doc in docs:
        doc["admin_units"] = admin_units_of(doc)
    n_admin = sum(1 for d in docs if d["admin_units"])
    train_docs, valid_docs = split_docs(docs)

    stats: Counter = Counter()
    print(f"=== Sinh mẫu kiểm chứng từ {len(docs)} bài "
          f"({len(train_docs)} train / {len(valid_docs)} valid) ===")
    print(f"  {n_admin}/{len(docs)} bài có địa danh hành chính trong câu định nghĩa")
    # Giới hạn theo MAX_SHARE của tập ĐANG CÓ: n_extra / (n_cũ + n_extra) <= share.
    # Đếm trên tập ĐÃ BỎ mẫu kiểm chứng cũ, nếu không thì lần chạy thứ hai lấy cap
    # tính từ một tập đã chứa mẫu kiểm chứng và ngưỡng bị nới ra mỗi lần chạy.
    n_old_train = sum(1 for r in read_jsonl(OUT_TRAIN) if not is_verify_sample(r))
    n_old_valid = sum(1 for r in read_jsonl(OUT_VALID) if not is_verify_sample(r))
    cap_train = int(n_old_train * MAX_SHARE / (1 - MAX_SHARE))
    cap_valid = int(n_old_valid * MAX_SHARE / (1 - MAX_SHARE))
    train_rows = rebalance(build(train_docs, rng, stats), rng, cap_train)
    valid_rows = rebalance(build(valid_docs, rng, stats), rng, cap_valid)

    print("\n=== Cổng ===")
    for reason, n in stats.most_common():
        print(f"  {reason:<44} {n}")

    bad = check_evidence(train_rows) + check_evidence(valid_rows)
    if bad:
        print(f"\nERROR: {len(bad)} mẫu có trích dẫn không nằm trong nguồn:")
        for line in bad[:10]:
            print(f"  {line}")
        return 1
    print("\n  OK: mọi trích dẫn đều là chuỗi có thật trong đoạn nguồn")

    bad = check_admin_evidence(train_rows) + check_admin_evidence(valid_rows)
    if bad:
        print(f"\nERROR: {len(bad)} mẫu địa danh có trích dẫn không chứng minh đáp án:")
        for line in bad[:10]:
            print(f"  {line}")
        return 1
    print("  OK: mọi mẫu địa danh có trích dẫn chứa chính địa danh nó khẳng định")

    # `places` = mọi tên nơi ĐÚNG của từng bài (vùng + phường/xã), lấy từ metadata.
    places = {d["name"]: {d["region"]} | set(d["admin_units"]) for d in docs}
    bad = (check_negative_truth(train_rows, places)
           + check_negative_truth(valid_rows, places))
    if bad:
        print(f"\nERROR: {len(bad)} mẫu phủ định có phán quyết trái metadata:")
        for line in bad[:10]:
            print(f"  {line}")
        return 1
    print("  OK: mọi mẫu phủ định có phán quyết khớp sự thật trong metadata")

    print("\n=== Cân bằng ===")
    balance_report(train_rows, "Train")
    balance_report(valid_rows, "Valid")

    write_jsonl(OUT_VERIFY_TRAIN, train_rows)
    write_jsonl(OUT_VERIFY_VALID, valid_rows)
    print(f"\n  → {OUT_VERIFY_TRAIN.relative_to(ROOT)}")
    print(f"  → {OUT_VERIFY_VALID.relative_to(ROOT)}")

    if not args.merge:
        print("\n  Xem mẫu rồi chạy lại với --merge để trộn vào tập train.")
        print("\n--- ví dụ 2 mẫu ---")
        for row in train_rows[:2]:
            print(f"\nQ: {row['messages'][1]['content'].split('Câu hỏi: ')[-1]}")
            print(f"A: {row['messages'][-1]['content'][:300]}")
        return 0

    for base, extra in ((OUT_TRAIN, train_rows), (OUT_VALID, valid_rows)):
        raw = read_jsonl(base)
        # BỎ mẫu kiểm chứng cũ trước khi trộn bộ mới. Không bỏ thì chạy lại lần hai
        # là cộng dồn - xem `is_verify_sample`.
        old = [r for r in raw if not is_verify_sample(r)]
        n_dropped = len(raw) - len(old)
        if n_dropped:
            print(f"\n  {base.name}: bỏ {n_dropped} mẫu kiểm chứng của lần chạy trước")
        n_sync = sync_system(old)
        if n_sync:
            print(f"  {base.name}: đồng bộ SYSTEM cho {n_sync} mẫu cũ "
                  "(prompt.py có quy tắc đính chính mới)")
        merged = old + extra
        rng.shuffle(merged)
        write_jsonl(base, merged)
        share = f"{len(extra) / len(merged):.0%}"
        print(f"  {base.name}: {len(old)} + {len(extra)} = {len(merged)} mẫu "
              f"(kiểm chứng chiếm {share})")

    # NER nằm ở file riêng (ner_train_v3.jsonl) nhưng cũng mang SYSTEM - phải
    # đồng bộ, nếu không nửa tập dùng prompt cũ nửa tập dùng prompt mới.
    for ner_path in (ROOT / "data" / "ner_train_v3.jsonl",
                     ROOT / "data" / "ner_valid_v3.jsonl"):
        if not ner_path.exists():
            continue
        rows = read_jsonl(ner_path)
        n_sync = sync_system(rows)
        if n_sync:
            write_jsonl(ner_path, rows)
            print(f"  {ner_path.name}: đồng bộ SYSTEM cho {n_sync} mẫu")

    n_train = len(read_jsonl(OUT_TRAIN))
    print(f"\n  Gợi ý iters cho lora_config.yaml (batch_size 2, ~3 epoch): "
          f"{max(n_train * 3 // 2, 100)}")
    print("  Train --fresh, ĐỪNG resume trên adapter cũ.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
