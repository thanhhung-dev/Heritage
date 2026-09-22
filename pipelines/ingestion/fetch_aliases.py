#!/usr/bin/env python3
"""Sinh corpus/aliases.json - tên gọi khác của mỗi bài trong corpus.

VÌ SAO CẦN: retrieval chỉ neo được vào miền tri thức khi câu hỏi gọi một tên mà
KG biết (apps/backend/core/kg.py:find_seeds). Người dùng gọi "nhà thờ con gà", không
gọi "Nhà thờ chính tòa Đà Nẵng"; BM25 vẫn tìm ra đúng bài (coverage 1.0) nhưng
cổng REQUIRE_GRAPH_ANCHOR trong rag.py ném sạch kết quả vì seeds rỗng.

HAI NGUỒN, cả hai đều KHÔNG bịa:
1. Redirect Wikipedia (cần mạng) - danh sách trang trỏ về cùng pageid. Đây là
   alias do người biên tập wiki tạo, chất lượng cao nhất. pageid lấy từ
   corpus/resolve_map.json nên không cần resolve lại.
2. Câu mở đầu của bài (offline) - wiki tiếng Việt rất đều: "hay còn gọi là",
   "thường được gọi tắt là". Giữ được nguyên tắc của kg.py: mọi tên đều truy
   được về một chuỗi có thật trong văn bản.

Artifact được COMMIT để runtime không bao giờ phải gọi mạng - cả backend đang
chạy offline được và phải giữ nguyên tính chất đó.

  # đủ hai nguồn (lần đầu, cần mạng)
  apps/backend/.venv/bin/python pipelines/ingestion/fetch_aliases.py

  # chỉ trích từ corpus, không gọi mạng
  apps/backend/.venv/bin/python pipelines/ingestion/fetch_aliases.py --no-net
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.backend.core.corpus import CORPUS_DIR, clean_wiki_text, load_docs  # noqa: E402
from apps.backend.core.textutil import nfc, strip_accents  # noqa: E402

ALIAS_FILE = ROOT / "corpus" / "aliases.json"
RESOLVE_MAP = ROOT / "corpus" / "resolve_map.json"

API = "https://vi.wikipedia.org/w/api.php"
USER_AGENT = "HeritageGraph/0.1 (academic research; vi-wiki heritage corpus)"
BATCH = 20          # giới hạn pageids mỗi request của MediaWiki API cho client thường

MIN_ALIAS_CHARS = 4  # "Huế", "Sơn" quá ngắn -> khớp bừa vào mọi bài

# Tên chung có thật ở nhiều tỉnh khác. Chỉ nhận khi CÒN KÈM region ("Nhà Thờ Lớn
# Đà Nẵng" nhận, "Nhà Thờ Lớn" không) - nếu không thì "Nhà thờ Lớn Hà Nội xây
# năm nào" sẽ neo vào bài Đà Nẵng và model trả lời rất tự tin về sai công trình.
GENERIC = frozenset({
    "nha tho lon", "nha tho chinh toa", "nha tho", "cho", "cho lon",
    "kinh thanh", "hoang thanh", "dai noi", "co do", "song huong",
    "chua", "lang", "dien", "thanh", "cung", "dan nam giao",
    "vien bao tang", "bao tang", "nha nhac", "nhac cung dinh", "festival",
})

REGIONS = ("Đà Nẵng", "Huế", "Thừa Thiên Huế", "Hội An", "Quảng Nam")

# Mẫu câu mở đầu wiki tiếng Việt. Chỉ quét câu ĐẦU của bài - càng xa đầu bài thì
# "còn gọi là" càng có thể đang nói về một thứ khác, không phải chủ thể.
LEAD_PATTERNS = (
    r"thường được gọi tắt là\s+(.+?)(?:,\s*là|\s+là\s|\.|;|\))",
    r"hay còn (?:được )?gọi là\s+(.+?)(?:,\s*là|\s+là\s|\.|;|\))",
    r"còn (?:được )?gọi là\s+(.+?)(?:,\s*là|\s+là\s|\.|;|\))",
    r"tên gọi khác(?:\s+là)?\s+(.+?)(?:,\s*là|\s+là\s|\.|;|\))",
    r"(?:còn |cũng )?được biết đến (?:với tên|như)\s+(.+?)(?:,\s*là|\s+là\s|\.|;|\))",
)
# Tách "A, B hoặc C" / "A hay B" thành từng tên.
SPLIT_ALIAS = re.compile(r"\s*(?:,|;|\bhoặc\b|\bhay\b|\bvà\b)\s*")

# Ngoặc phân biệt của wiki: "Sơn Trà (bán đảo)" -> "Sơn Trà".
# Phải cắt TRƯỚC khi _norm() strip dấu ")" ở cuối, nếu không "Sơn Trà (bán đảo)"
# thành "Sơn Trà (bán đảo" - ngoặc lẻ, không mẫu nào khớp được nữa.
PAREN = re.compile(r"\s*\(.*$")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", nfc(s)).strip(" ,.;:\"'“”()")


def _plain(s: str) -> str:
    return strip_accents(_norm(s))


def _valid(alias: str, doc_name: str) -> bool:
    """Alias hợp lệ về hình thức (chưa xét xung đột giữa các bài)."""
    a = _norm(alias)
    if len(a) < MIN_ALIAS_CHARS or len(a) > 60:
        return False
    if _plain(a) == _plain(doc_name):
        return False
    if _plain(a) in GENERIC:
        return False
    # phải là tên riêng, không phải một mệnh đề bị regex bắt lỡ
    if len(a.split()) > 6:
        return False
    # chứa ít nhất một chữ; loại "156 Trần Phú" kiểu địa chỉ thuần số
    return bool(re.search(r"[^\W\d_]", a, re.UNICODE))


def _variants(alias: str) -> list[str]:
    """Alias + biến thể bỏ region ở cuối.

    "Nhà thờ con gà Đà Nẵng" -> thêm "Nhà thờ con gà", vì người dùng gõ tên ngắn.
    Biến thể ngắn chỉ nhận khi KHÔNG rơi vào GENERIC (xử ở _valid).
    """
    out = [alias]
    for region in REGIONS:
        if alias.endswith(" " + region):
            out.append(alias[: -len(region) - 1].strip())
            break
    return out


# --- Nguồn 1: redirect Wikipedia ---------------------------------------------

def fetch_redirects(pageids: list[int]) -> dict[str, list[str]]:
    """{tiêu đề bài: [tên redirect]} - gọi API theo lô, không resolve lại tên."""
    out: dict[str, list[str]] = {}
    for i in range(0, len(pageids), BATCH):
        chunk = "|".join(str(p) for p in pageids[i : i + BATCH])
        url = (f"{API}?action=query&prop=redirects&pageids={urllib.parse.quote(chunk)}"
               "&rdlimit=500&rdnamespace=0&format=json")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        for page in data.get("query", {}).get("pages", {}).values():
            titles = [r["title"] for r in page.get("redirects", [])]
            if titles:
                out[page["title"]] = titles
    return out


def aliases_from_redirects(doc_names: set[str]) -> dict[str, list[str]]:
    """Map redirect về TÊN BÀI TRONG CORPUS, không phải tiêu đề wiki.

    resolve_map.json giữ cả hai: `name` (tên trong corpus) và `resolved_title`
    (tiêu đề thật trên wiki). Chúng lệch nhau ở vài bài - "Bán đảo Sơn Trà" nằm
    ở trang "Sơn Trà" - nên bản thân `resolved_title` cũng là một alias tốt.
    """
    entries = json.loads(RESOLVE_MAP.read_text("utf-8"))
    wanted = [e for e in entries if e["name"] in doc_names and e.get("pageid")]
    if not wanted:
        return {}

    by_title = fetch_redirects([e["pageid"] for e in wanted])
    out: dict[str, list[str]] = {}
    for e in wanted:
        found = list(by_title.get(e["resolved_title"], []))
        if e["resolved_title"] != e["name"]:
            found.append(e["resolved_title"])
        if found:
            out[e["name"]] = found
    return out


# --- Nguồn 2: câu mở đầu bài -------------------------------------------------

def aliases_from_lead(name: str, text: str) -> list[str]:
    """Trích tên gọi khác từ đoạn mở đầu."""
    lead = clean_wiki_text(text).split("\n", 1)[0]
    lead = nfc(lead)[:600]
    found: list[str] = []
    for pat in LEAD_PATTERNS:
        for m in re.finditer(pat, lead, re.IGNORECASE):
            for part in SPLIT_ALIAS.split(m.group(1)):
                part = _norm(part)
                if part:
                    found.append(part)
    return found


# --- Hợp nhất & lọc xung đột -------------------------------------------------

def build(doc_names: set[str], use_net: bool) -> tuple[dict[str, list[str]], list[str]]:
    """Trả về ({tên bài: [alias]}, log dòng để in ra)."""
    log: list[str] = []
    raw: dict[str, list[str]] = {n: [] for n in doc_names}

    if use_net:
        try:
            for name, aliases in aliases_from_redirects(doc_names).items():
                raw[name].extend(aliases)
            log.append(f"redirect wiki: {sum(1 for v in raw.values() if v)} bài có alias")
        except Exception as exc:                       # noqa: BLE001
            log.append(f"redirect wiki THẤT BẠI ({exc}) - chỉ dùng câu mở đầu")

    for name in doc_names:
        path = CORPUS_DIR / f"{name}.txt"
        if path.exists():
            raw[name].extend(aliases_from_lead(name, path.read_text("utf-8")))

    # Lọc hình thức + sinh biến thể bỏ region
    shaped: dict[str, set[str]] = {}
    for name, aliases in raw.items():
        keep: set[str] = set()
        for alias in aliases:
            for cand in _variants(_norm(PAREN.sub("", nfc(alias)))):
                if _valid(cand, name):
                    keep.add(cand)
        if keep:
            shaped[name] = keep

    # XUNG ĐỘT. Hai loại, cả hai đều phải bỏ:
    #  - alias trùng tên một bài khác: lead của "Kinh thành Huế" liệt kê
    #    "Hoàng thành Huế" - nhận thì hỏi bài này neo sang bài kia.
    #  - alias bị hai bài cùng nhận ("Đại nội Huế"): không biết trỏ về đâu.
    doc_plain = {_plain(n): n for n in doc_names}
    owners: dict[str, set[str]] = {}
    for name, aliases in shaped.items():
        for alias in aliases:
            owners.setdefault(_plain(alias), set()).add(name)

    out: dict[str, list[str]] = {}
    for name, aliases in shaped.items():
        kept: list[str] = []
        for alias in sorted(aliases):
            key = _plain(alias)
            if key in doc_plain and doc_plain[key] != name:
                log.append(f"  bỏ '{alias}' ({name}): trùng tên bài '{doc_plain[key]}'")
                continue
            if len(owners[key]) > 1:
                log.append(f"  bỏ '{alias}': {len(owners[key])} bài cùng nhận "
                           f"({', '.join(sorted(owners[key]))})")
                continue
            kept.append(alias)
        if kept:
            out[name] = kept
    return out, log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-net", action="store_true",
                    help="Chỉ trích từ câu mở đầu, không gọi Wikipedia API")
    args = ap.parse_args()

    docs, _skipped = load_docs()
    doc_names = {d["name"] for d in docs}
    aliases, log = build(doc_names, use_net=not args.no_net)

    for line in log:
        print(line)
    ALIAS_FILE.write_text(
        json.dumps(dict(sorted(aliases.items())), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    total = sum(len(v) for v in aliases.values())
    print(f"\n{ALIAS_FILE.relative_to(ROOT)}: {total} alias / {len(aliases)}"
          f" bài (trên {len(doc_names)} bài trong corpus)")
    for name, al in sorted(aliases.items()):
        print(f"  {name}: {', '.join(al)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
