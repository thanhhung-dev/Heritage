#!/usr/bin/env python3
"""
Tạo gold eval set mẫu (5 mẫu minh họa) cho task NER + QA + Refusal.
Bạn cần mở rộng lên ~100 mẫu, gán nhãn tay, rồi dùng scripts/score_gold.py để đánh giá.

Chạy: python scripts/make_gold_template.py
"""
import json
from pathlib import Path

EVAL = Path(__file__).resolve().parents[1] / "evaluation"
EVAL.mkdir(parents=True, exist_ok=True)

gold = [
    # ---- NER ----
    {
        "id": "ner-001",
        "task": "ner",
        "input": "Nghệ nhân Nguyễn Văn A (1912-1985) quê làng gốm Bát Tràng, thường trình diễn tại hội làng đầu xuân.",
        "expected": {
            "người": ["Nguyễn Văn A"],
            "địa điểm": ["làng gốm Bát Tràng"],
            "sự kiện": ["hội làng đầu xuân"],
            "thời gian": ["1912-1985"],
        },
    },
    {
        "id": "ner-002",
        "task": "ner",
        "input": "Làng tranh Đông Hồ thuộc huyện Thuận Thành, tỉnh Bắc Ninh, nổi tiếng từ thế kỷ XVII.",
        "expected": {
            "người": [],
            "địa điểm": ["Làng tranh Đông Hồ", "huyện Thuận Thành", "tỉnh Bắc Ninh"],
            "sự kiện": [],
            "thời gian": ["thế kỷ XVII"],
        },
    },
    # ---- QA có trích dẫn ----
    {
        "id": "qa-001",
        "task": "qa",
        "input": "Hội thi thổi cơm diễn ra khi nào và ở đâu?",
        "source": "Hội thi thổi cơm làng Đường Lâm diễn ra ngày mùng 4 tháng Giêng hằng năm.",
        "expected_citations": ["Hội thi thổi cơm làng Đường Lâm diễn ra ngày mùng 4 tháng Giêng hằng năm"],
    },
    # ---- Refusal ----
    {
        "id": "refusal-001",
        "task": "refusal",
        "input": "Lễ hội Đền Hùng có nguồn gốc từ thời nào?",
        "source": "",
        "expected_refusal": True,
    },
    {
        "id": "refusal-002",
        "task": "refusal",
        "input": "Kể tên các làng gốm nổi tiếng ở Việt Nam.",
        "source": "Làng gốm Bát Tràng thuộc Hà Nội.",
        "expected_refusal": False,
    },
]

out = EVAL / "gold.jsonl"
with out.open("w", encoding="utf-8") as f:
    for s in gold:
        f.write(json.dumps(s, ensure_ascii=False) + "\n")

print(f"wrote {len(gold)} gold samples → {out}")
print("Mở rộng lên ~100 mẫu, gán nhãn tay, rồi chạy scripts/score_gold.py")
