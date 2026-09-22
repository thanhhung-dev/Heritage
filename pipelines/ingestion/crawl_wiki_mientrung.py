#!/usr/bin/env python3
"""
Crawl Wikipedia VI về văn hóa dân gian Đà Nẵng - Huế (miền Trung).
- BFS từ seed topics
- Lọc theo keyword miền Trung
- Lưu text thô vào corpus/wiki/
- Có thể chạy resume: skip bài đã có

Usage:
  python scripts/crawl_wiki_mientrung.py
  python scripts/crawl_wiki_mientrung.py --max 500
  python scripts/crawl_wiki_mientrung.py --seed-only  # chỉ lấy bài seed
"""
import argparse
import re
import wikipediaapi
from pathlib import Path
from time import sleep

# ---------- Cấu hình ----------
CORPUS_DIR = Path("corpus/wiki")
CORPUS_DIR.mkdir(parents=True, exist_ok=True)

# Keyword lọc bài "liên quan miền Trung"
MT_KEYWORDS = [
    "Huế", "Thừa Thiên", "Đà Nẵng", "Quảng Nam", "Quảng Ngãi",
    "miền Trung", "xứ Huế", "cung đình", "miền Trung Việt Nam",
    "Festival Huế", "sông Hương", "sông Hàn", "Non Nước",
    "Bà Nà", "Ngũ Hành Sơn", "Hội An",
]

# Seed topics — bắt đầu BFS từ đây
SEEDS = [
    # === Huế ===
    "Huế",
    "Nhã nhạc cung đình Huế",
    "Ca Huế",
    "Festival Huế",
    "Cung đình Huế",
    "Lăng tẩm Huế",
    "Hoàng thành Huế",
    "Chùa Thiên Mụ",
    "Đại Nội Huế",
    "Sông Hương",
    "Lụa Mỹ Xuyên",
    "Đúc đồng Huế",
    "Múa bóng",
    "Bài chòi",
    "Ca dao Huế",
    "Ẩm thực cung đình Huế",
    "Võ Thị Sáu (Huế)",
    "Lễ hội Cầu Ngư",
    "Nghệ thuật Ca Huế",
    "Đờn ca tài tử Nam Bộ",  # để có context so sánh
    # === Đà Nẵng ===
    "Đà Nẵng",
    "Ngũ Hành Sơn",
    "Bà Nà Hills",
    "Sông Hàn",
    "Biển Mỹ Khê",
    "Làng đá Non Nước",
    "Làng La Hường",
    "Gốm Thanh Hà",
    "Nước mắm Nam Ô",
    "Bánh tráng Cẩm Lệ",
    "Lễ hội Quan Thế Âm",
    "Đua thuyền sông Hàn",
    "Đình làng Cẩm Lệ",
    "Múa xứ Dừa",
    "Bài chòi miền Trung",
    "Cầu Rồng",
    "Bảo tàng Chăm",
    # === Di sản chung ===
    "Di sản thế giới tại Việt Nam",
    "Nhã nhạc cung đình",
    "Bài chòi",
    "Hát bội",
    "Múa rối nước",
    "Văn hóa miền Trung",
    "Làng nghề truyền thống Việt Nam",
    "Lễ hội truyền thống Việt Nam",
]

# Bài stub cần bỏ
STUB_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"đây là bài stub",
        r"chưa có nội dung",
        r"^\s*#\s*định hướng",
    ]
]


def is_relevant(text: str, title: str) -> bool:
    """Bài phải có ≥ 2 keyword miền Trung hoặc nằm trong whitelist."""
    combined = f"{title} {text[:500]}"
    hits = sum(1 for kw in MT_KEYWORDS if kw.lower() in combined.lower())
    return hits >= 1 and len(text) > 500


def is_stub(text: str) -> bool:
    return any(p.search(text) for p in STUB_PATTERNS) or len(text) < 400


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=500, help="số bài tối đa")
    ap.add_argument("--seed-only", action="store_true", help="chỉ lấy bài seed")
    ap.add_argument("--resume", action="store_true", help="skip bài đã có")
    args = ap.parse_args()

    wiki = wikipediaapi.Wikipedia(
        user_agent="vh-mientrung-bot/1.0 (vanhoa-chatbot)",
        language="vi",
    )

    visited = set()
    queue = list(SEEDS)

    # resume: load title đã có
    if args.resume:
        for f in CORPUS_DIR.glob("*.txt"):
            visited.add(f.stem.replace("_", "/"))
        print(f"[resume] {len(visited)} bài đã có, bỏ qua")

    saved = 0
    while queue and saved < args.max:
        title = queue.pop(0)
        if title in visited:
            continue
        visited.add(title)

        try:
            page = wiki.page(title)
        except Exception as e:
            print(f"[ERR] {title}: {e}")
            continue

        if not page.exists():
            continue

        text = page.text
        if is_stub(text):
            continue
        if not is_relevant(text, title):
            print(f"[skip] {title} (không liên quan miền Trung)")
            continue

        # Lưu
        out_path = CORPUS_DIR / f"{title.replace('/', '_')}.txt"
        out_path.write_text(text, "utf-8")
        saved += 1
        print(f"[{saved}] {title} ({len(text)} chars)")

        # BFS sang bài liên quan
        if not args.seed_only:
            for link in page.links.values():
                if link not in visited and len(queue) < 2000:
                    queue.append(link)

        sleep(0.1)  # rate limit friendly

    print(f"\ndone. saved {saved} bài → {CORPUS_DIR}")


if __name__ == "__main__":
    main()
