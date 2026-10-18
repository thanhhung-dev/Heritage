#!/usr/bin/env python3
"""
Crawl Wikipedia theo từng địa điểm trong danh sách Huế - Đà Nẵng.
Mỗi địa điểm → 1 file .txt chứa nội dung Wikipedia.

Output:
  corpus/wiki_by_location/<tên địa điểm>.txt
  corpus/locations_index.json (metadata)
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipelines.training.locations_hue_danang import get_all_locations

try:
    import wikipediaapi
except ImportError:
    print("ERROR: cài wikipedia-api: pip install wikipedia-api")
    sys.exit(1)


CORPUS_DIR = Path("corpus/wiki_by_location")
INDEX_FILE = Path("corpus/locations_index.json")
CORPUS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    locations = get_all_locations()
    print(f"=== Crawl {len(locations)} địa điểm Huế - Đà Nẵng ===\n")

    wiki = wikipediaapi.Wikipedia(
        user_agent="vh-danang-hue-bot/1.0 (vanhoa-chatbot)",
        language="vi",
    )

    results = []
    failed = []

    for i, loc in enumerate(locations, 1):
        name = loc["name"]
        # Skip nếu đã crawl
        out_path = CORPUS_DIR / f"{name.replace('/', '_')}.txt"
        if out_path.exists() and out_path.stat().st_size > 200:
            print(f"[{i}/{len(locations)}] ⏭  {name} (đã có)")
            results.append({
                "region": loc["region"],
                "category": loc["category"],
                "name": name,
                "chars": out_path.stat().st_size,
                "file": out_path.name,
            })
            continue

        print(f"[{i}/{len(locations)}]  {name} ({loc['region']}) ...", end=" ")

        try:
            page = wiki.page(name)
            if page.exists() and len(page.text) > 200:
                out_path.write_text(page.text, "utf-8")
                results.append({
                    "region": loc["region"],
                    "category": loc["category"],
                    "name": name,
                    "chars": len(page.text),
                    "file": out_path.name,
                    "url": page.fullurl,  # Lưu URL gốc Wikipedia
                })
                print(f"✓ {len(page.text)} chars - {page.fullurl}")
            else:
                failed.append({**loc, "reason": "không tồn tại hoặc quá ngắn"})
                print("✗ không có")
        except Exception as e:
            failed.append({**loc, "reason": str(e)})
            print(f"✗ {e}")

        time.sleep(0.15)  # rate limit

    # Lưu index
    INDEX_FILE.write_text(
        json.dumps({
            "success": results,
            "failed": failed,
            "total_success": len(results),
            "total_failed": len(failed),
        }, ensure_ascii=False, indent=2),
        "utf-8"
    )

    print(f"\n=== Done ===")
    print(f"Thành công: {len(results)}")
    print(f"Thất bại: {len(failed)}")
    if failed:
        print(f"\n  Các địa điểm thất bại:")
        for f in failed:
            print(f"    - {f['name']} ({f['reason']})")
    print(f"\n  Index: {INDEX_FILE}")
    print(f"  Corpus: {CORPUS_DIR}/")


if __name__ == "__main__":
    main()
