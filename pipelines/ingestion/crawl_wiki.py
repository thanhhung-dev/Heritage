#!/usr/bin/env python3
"""Crawl Wikipedia tiếng Việt cho danh sách địa điểm - giải tên bằng search API.

Vì sao cần file này thay cho pipelines/ingestion/crawl_by_location.py: bản cũ gọi
wiki.page(name) tức là tra ĐÚNG TIÊU ĐỀ. Tên trong locations_hue_danang.py là tên
mô tả ("Bà Nà Hills", "Làng đá Non Nước", "Lễ hội Cầu Ngư") nên 24/49 địa điểm
trượt, dù bài thật có tồn tại ("Bà Nà", "Làng Non Nước", "Lễ Cầu ngư").

Hai bước, KHÔNG gộp: bước resolve chỉ ghi bảng ánh xạ để soát, bước fetch mới ghi
lên corpus. Search API trả về cả bài sai (tra "Làng gốm Thanh Hà" thì top-1 là
"Hội An (thành phố)"), nên tự động lấy top-1 là bơm rác vào corpus -> vào graph ->
vào nhãn NER.

  # 1. Giải tên, ghi corpus/resolve_map.json (chỉ đọc, không sửa corpus)
  apps/backend/.venv/bin/python pipelines/ingestion/crawl_wiki.py resolve

  # 2. Soát: sửa "skip": true cho dòng nào sai, hoặc sửa tay "resolved_title"
  #    Các dòng "review": true là chỗ script không tự tin, soát trước.

  # 3. Tải về theo đúng bảng đã soát (có backup corpus cũ)
  apps/backend/.venv/bin/python pipelines/ingestion/crawl_wiki.py fetch
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.backend.core.textutil import strip_accents  # noqa: E402
from pipelines.training.locations_hue_danang import get_all_locations  # noqa: E402

CORPUS_DIR = ROOT / "corpus" / "wiki_by_location"
INDEX_FILE = ROOT / "corpus" / "locations_index.json"
MAP_FILE = ROOT / "corpus" / "resolve_map.json"

API = "https://vi.wikipedia.org/w/api.php"
UA = {"User-Agent": "heritagegraph-bot/1.0 (do an tot nghiep; vi.wikipedia)"}

MIN_CHARS = 400        # ngắn hơn mức này thì chunk_corpus không dùng được
MIN_WORDCOUNT = 60     # loại stub trong kết quả search

# Bài "cha" luôn đứng đầu search vì dài, nhưng nội dung là cả thành phố/tỉnh.
BLOCKLIST = {strip_accents(x).lower() for x in (
    "Đà Nẵng", "Huế", "Thành phố Huế", "Hà Nội", "Việt Nam", "Quảng Nam",
    "Quảng Ngãi", "Thừa Thiên Huế", "Sun Group", "Làng nghề Việt Nam",
    "Lễ hội Việt Nam", "Hội An (thành phố)", "Ẩm thực Việt Nam",
)}

# Từ chỉ loại - bỏ khỏi phần "lõi" của tên khi so khớp, vì tiêu đề bài thật
# thường không mang chúng ("Lễ hội Cầu Ngư" -> "Lễ Cầu ngư").
GENERIC = {strip_accents(x) for x in (
    "le", "hoi", "lang", "nghe", "bien", "bai", "di", "tich", "lich", "su",
    "mon", "an", "dac", "san", "khu", "du", "hills", "mien", "trung", "va",
    "cua", "o", "tai", "thanh", "pho", "lam", "day", "det",
)}

# Tiêu đề bài thật phải chứa ít nhất một trong các gợi ý này, nếu không thì cờ
# review. Chặn ca "Lễ hội Quan Thế Âm" -> "Quán Thế Âm" (bài về Bồ Tát, không
# phải về lễ hội): điểm khớp tên là 1.0 nhưng tiêu đề không có chữ lễ/hội nào.
CATEGORY_HINTS = {
    "Lễ hội": ("le", "hoi"),
    "Làng nghề": ("lang", "phuong", "nghe"),
}

# Trùng tên giữa các vùng là chuyện thường: "Đàn Nam Giao" có bản Huế và bản
# Thăng Long, cùng điểm khớp tên 1.0 và bản Thăng Long dài hơn. Không kiểm vùng
# thì corpus Huế - Đà Nẵng nhận bài về Hà Nội.
REGION_WORDS = {
    "Huế": ("hue", "thua thien"),
    "Đà Nẵng": ("da nang", "quang nam", "hoi an"),
}


# ---------- API ----------

# Cache trên đĩa: vi.wikipedia trả 429 khá sớm, và bước resolve gọi ~120 lần.
# Có cache thì chạy lại là tiếp tục chỗ dở, không phải gọi lại từ đầu.
CACHE_DIR = ROOT / "corpus" / ".wiki_cache"


def api(**params) -> dict:
    """Có cache đĩa + backoff tôn trọng Retry-After."""
    params.update(format="json", utf8="1")
    query = urllib.parse.urlencode(sorted(params.items()))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / (hashlib.sha1(query.encode()).hexdigest() + ".json")
    if cache.exists():
        return json.loads(cache.read_text("utf-8"))

    req = urllib.request.Request(API + "?" + query, headers=UA)
    delay = 2.0
    for attempt in range(7):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            cache.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
            return data
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or attempt == 6:
                raise
            wait = float(e.headers.get("Retry-After") or delay)
            print(f"    (HTTP {e.code}, chờ {wait:.0f}s)", file=sys.stderr)
            time.sleep(wait)
            delay = min(delay * 2, 60)
    return {}


def search(term: str, limit: int = 8) -> list[dict]:
    d = api(action="query", list="search", srsearch=term, srlimit=limit)
    return d.get("query", {}).get("search", [])


def get_page(title: str) -> dict | None:
    """Lấy full plaintext + pageid + url. Theo redirect, nhận diện trang định hướng."""
    d = api(action="query", prop="extracts|info|pageprops", explaintext="1",
            inprop="url", redirects="1", titles=title)
    pages = d.get("query", {}).get("pages", {})
    if not pages:
        return None
    pg = next(iter(pages.values()))
    if "missing" in pg:
        return None
    return {
        "pageid": pg.get("pageid"),
        "title": pg.get("title"),
        "url": pg.get("fullurl"),
        "text": pg.get("extract", "") or "",
        "is_disambig": "disambiguation" in (pg.get("pageprops") or {}),
    }


# ---------- Khớp tên ----------

def tokens(s: str) -> set[str]:
    return {t for t in strip_accents(s).lower().replace("(", " ").replace(")", " ").split() if t}


def core_tokens(name: str) -> set[str]:
    """Phần định danh của tên, bỏ từ chỉ loại. Không bao giờ trả về rỗng."""
    tk = tokens(name)
    return (tk - GENERIC) or tk


def score(name: str, cand_title: str) -> float:
    core = core_tokens(name)
    return len(core & tokens(cand_title)) / len(core)


def region_ok(loc_region: str, *texts: str) -> bool:
    blob = strip_accents(" ".join(t or "" for t in texts)).lower()
    return any(w in blob for w in REGION_WORDS.get(loc_region, ()))


def resolve_one(loc: dict) -> dict:
    """Chọn bài Wikipedia cho một địa điểm, kèm pageid/url/số ký tự."""
    name = loc["name"]
    row: dict = {"name": name, "category": loc["category"], "region": loc["region"]}

    def accept(pg: dict, how: str, sc: float, review: bool, why: str | None) -> dict:
        return {**row, "resolved_title": pg["title"], "pageid": pg["pageid"],
                "url": pg["url"], "chars": len(pg["text"]), "how": how,
                "score": sc, "review": review, "why_review": why}

    # 1. Đúng tiêu đề là bằng chứng mạnh nhất. Trang định hướng ("Đàn Nam Giao")
    #    không tính - phải xuống search để lấy bài thật.
    exact = get_page(name)
    if exact and not exact["is_disambig"] and len(exact["text"]) >= MIN_CHARS:
        return accept(exact, "exact", 1.0, False, None)

    # 2. Search + cho điểm theo phần lõi của tên.
    hits = search(name)
    scored = []
    for h in hits:
        t = h["title"]
        if strip_accents(t).lower() in BLOCKLIST or h.get("wordcount", 0) < MIN_WORDCOUNT:
            continue
        scored.append((score(name, t), h.get("wordcount", 0), t))
    scored.sort(reverse=True)

    if not scored:
        return {**row, "resolved_title": None, "how": "no-candidate", "score": 0.0,
                "review": True, "skip": True,
                "why_review": "vi.wikipedia không có bài riêng cho mục này",
                "alternatives": [h["title"] for h in hits]}

    best = scored[0][0]
    tied = [t for sc, _, t in scored if sc == best][:4]

    # Nhiều bài cùng điểm -> tách bằng VÙNG, đọc trong nội dung bài chứ không chỉ
    # tiêu đề: "Đàn Nam Giao (triều Nguyễn)" không có chữ "Huế" trong tiêu đề.
    chosen, ambiguous = None, False
    if len(tied) > 1:
        matches = []
        for t in tied:
            pg = get_page(t)
            time.sleep(0.4)
            if pg and len(pg["text"]) >= MIN_CHARS and region_ok(loc["region"], pg["text"][:3000]):
                matches.append(pg)
        if len(matches) == 1:
            chosen = matches[0]
        elif len(matches) > 1:
            chosen = max(matches, key=lambda p: len(p["text"]))
            ambiguous = True
    if chosen is None:
        chosen = get_page(tied[0])
        if not chosen or len(chosen["text"]) < MIN_CHARS:
            return {**row, "resolved_title": tied[0], "how": "search", "score": round(best, 2),
                    "review": True, "skip": True, "why_review": "bài quá ngắn",
                    "alternatives": [t for _, _, t in scored[1:4]]}

    hints = CATEGORY_HINTS.get(loc["category"])
    hint_ok = (not hints) or any(h in strip_accents(chosen["title"]).lower() for h in hints)
    in_region = region_ok(loc["region"], chosen["title"], chosen["text"][:3000])
    why = ("điểm khớp thấp" if best < 0.75 else
           f"tiêu đề không mang dấu hiệu {loc['category']!r}" if not hint_ok else
           f"nội dung không nhắc tới {loc['region']}" if not in_region else
           "nhiều bài cùng điểm, cùng vùng" if ambiguous else None)
    out = accept(chosen, "search", round(best, 2), why is not None, why)
    out["alternatives"] = [t for _, _, t in scored[1:4]]
    return out


# ---------- Bước resolve ----------

def cmd_resolve() -> int:
    locations = get_all_locations()
    print(f"=== Giải tên {len(locations)} địa điểm trên vi.wikipedia ===\n")
    rows = []
    for i, loc in enumerate(locations, 1):
        row = resolve_one(loc)
        rows.append(row)
        flag = "  " if not row["review"] else "?!"
        print(f"[{i:>2}/{len(locations)}] {flag} {loc['name']:<32} -> "
              f"{row.get('resolved_title') or '(không có bài)'}"
              f"  [{row['how']} {row['score']}]")
        time.sleep(0.4)

    MAP_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=2), "utf-8")

    auto = [r for r in rows if not r["review"]]
    rev = [r for r in rows if r["review"] and not r.get("skip")]
    none_ = [r for r in rows if r.get("skip")]
    print(f"\n=== {len(auto)} tự tin | {len(rev)} cần soát | {len(none_)} không có bài ===")
    for r in rev:
        print(f"  SOÁT  {r['name']:<32} -> {r['resolved_title']}  ({r['why_review']})")
        print(f"        khác: {r.get('alternatives')}")
    for r in none_:
        print(f"  TRỐNG {r['name']:<32} search ra: {r.get('alternatives')}")
    print(f"\n  Bảng ánh xạ: {MAP_FILE}")
    print("  Sửa 'resolved_title' hoặc đặt 'skip': true cho dòng sai, rồi chạy: "
          "pipelines/ingestion/crawl_wiki.py fetch")
    return 0


# ---------- Bước fetch ----------

def cmd_fetch(force: bool) -> int:
    if not MAP_FILE.exists():
        print(f"Chưa có {MAP_FILE}. Chạy `resolve` trước.")
        return 1
    rows = json.loads(MAP_FILE.read_text("utf-8"))
    todo = [r for r in rows if r.get("resolved_title") and not r.get("skip")]
    pending = [r for r in todo if r.get("review")]
    if pending and not force:
        print(f"Còn {len(pending)} dòng cờ review chưa soát:")
        for r in pending:
            print(f"  {r['name']:<32} -> {r['resolved_title']}  ({r.get('why_review')})")
        print("\nSoát trong resolve_map.json rồi đặt \"review\": false, "
              "hoặc \"skip\": true. Muốn lấy hết bất chấp: thêm --force.")
        return 1

    # Corpus là gốc của graph + gold set + số trong docs. Luôn backup trước khi ghi.
    if CORPUS_DIR.exists():
        bak = CORPUS_DIR.with_name(CORPUS_DIR.name + ".bak")
        if bak.exists():
            shutil.rmtree(bak)
        shutil.copytree(CORPUS_DIR, bak)
        print(f"==> Backup corpus cũ -> {bak}")
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    success, failed, seen_pageid = [], [], {}
    for i, r in enumerate(todo, 1):
        pg = get_page(r["resolved_title"])
        if not pg or len(pg["text"]) < MIN_CHARS:
            failed.append({**r, "reason": f"bài rỗng/quá ngắn ({len(pg['text']) if pg else 0} ký tự)"})
            print(f"[{i:>2}/{len(todo)}] ✗ {r['name']} -> {r['resolved_title']}")
            time.sleep(0.4)
            continue

        # Hai địa điểm có thể trỏ về cùng một bài ("Bánh khoái" redirect sang
        # "Bánh xèo"). Ghi hai file giống nhau là đếm trùng: corpus 25 bài nhưng
        # chỉ 23 nội dung khác nhau, mọi thống kê lệch theo.
        if pg["pageid"] in seen_pageid:
            failed.append({**r, "reason": f"trùng bài với {seen_pageid[pg['pageid']]!r}"})
            print(f"[{i:>2}/{len(todo)}] = {r['name']} trùng {seen_pageid[pg['pageid']]}")
            time.sleep(0.4)
            continue
        seen_pageid[pg["pageid"]] = r["name"]

        fname = r["name"].replace("/", "_") + ".txt"
        (CORPUS_DIR / fname).write_text(pg["text"], "utf-8")
        success.append({"region": r["region"], "category": r["category"], "name": r["name"],
                        "resolved_title": pg["title"], "pageid": pg["pageid"],
                        "url": pg["url"], "chars": len(pg["text"]), "file": fname})
        print(f"[{i:>2}/{len(todo)}] ✓ {r['name']:<32} {len(pg['text']):>6} ký tự  "
              f"({pg['title']})")
        time.sleep(0.4)

    failed += [{**r, "reason": r.get("why_review") or "không có bài trên vi.wikipedia"}
               for r in rows if r.get("skip") or not r.get("resolved_title")]
    INDEX_FILE.write_text(json.dumps(
        {"success": success, "failed": failed,
         "total_success": len(success), "total_failed": len(failed)},
        ensure_ascii=False, indent=2), "utf-8")

    total = sum(s["chars"] for s in success)
    print(f"\n=== {len(success)} bài, {total:,} ký tự | {len(failed)} bỏ ===")
    print(f"  Index: {INDEX_FILE}  (mỗi bài có 'url' thật - model không phải nhớ url)")
    print("\n  Sau khi cào lại PHẢI làm tiếp, vì corpus là gốc của mọi thứ:")
    print("    apps/backend/.venv/bin/python pipelines/graph/build_graph.py        # graph đổi node/edge")
    print("    apps/backend/.venv/bin/python pipelines/evaluation/eval_retrieval.py        # kiểm cổng từ chối")
    print("    apps/backend/.venv/bin/python pipelines/training/bootstrap_deep_qa.py # sinh lại data")
    print("    apps/backend/.venv/bin/python pipelines/evaluation/make_gold_template.py    # gold set mới")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["resolve", "fetch"])
    ap.add_argument("--force", action="store_true",
                    help="fetch: lấy cả các dòng còn cờ review")
    args = ap.parse_args()
    return cmd_resolve() if args.step == "resolve" else cmd_fetch(args.force)


if __name__ == "__main__":
    raise SystemExit(main())
