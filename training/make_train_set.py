#!/usr/bin/env python3
"""Gộp các file _v3 thành data/train.jsonl + data/valid.jsonl để trainer đọc.

VÌ SAO CẦN FILE NÀY
  1. Trainer đọc đúng `train_file` và `valid_file` trong lora_config.yaml. Các
     file `_v3.jsonl` chỉ được dùng sau khi chủ động gộp hoặc trỏ config vào đó.
  2. bootstrap_v3.py ghi NER ra file RIÊNG (ner_train_v3.jsonl) để đo copy-rate
     cho sạch - phần thân bài QA không bị 48 mẫu JSON làm loãng số liệu. Nhưng
     tách file KHÔNG có nghĩa là loại khỏi training: backend/core/llm.py serve
     MỘT adapter duy nhất cho cả trả lời QA và trích entity, nên nếu NER không
     vào train.jsonl thì model mất hẳn khả năng NER (base chỉ đạt F1 0.08, xem
     eval/report_base.json). Ở đây gộp lại, có kiểm soát tỉ lệ.

Chạy:
  backend/.venv/bin/python training/make_train_set.py            # gộp + sao lưu
  backend/.venv/bin/python training/make_train_set.py --ner-ratio 0.15
  backend/.venv/bin/python training/make_train_set.py --dry-run   # chỉ xem
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from training.bootstrap_deep_qa import SEED  # noqa: E402

DATA = ROOT / "data"

# Tỉ lệ mẫu NER tối đa trong tập train. NER là task phụ (chỉ 1 trong 4 metric ở
# score_gold.py) nhưng mẫu NER ngắn và định dạng cố định nên rất "dễ" - để tỉ lệ
# cao thì model dồn sức học JSON và nhả văn phong QA. 0.20 giữ NER đủ để F1 lên
# khỏi mức base mà không lấn sang task chính.
NER_RATIO = 0.20


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        print(f"ERROR: thiếu {path}. Chạy training/bootstrap_v3.py trước.")
        sys.exit(1)
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def kind(row: dict) -> str:
    """Phân loại mẫu để báo cáo thành phần tập dữ liệu."""
    answer = row["messages"][-1]["content"].lstrip()
    if answer.startswith("{"):
        return "ner"
    return "qa" if "[Nguồn:" in answer else "refusal"


def compose(qa_rows: list[dict], ner_rows: list[dict], ratio: float,
            rng: random.Random) -> tuple[list[dict], int]:
    """Trộn NER vào tập QA sao cho NER chiếm <= `ratio` tổng số mẫu.

    Cắt bớt NER thay vì nhân bản QA: nhân bản trên tập ~400 mẫu là đường ngắn
    nhất tới overfit, mà chính overfit (train loss 0.001) là lỗi đang phải sửa.
    """
    if ratio <= 0:
        return list(qa_rows), 0
    # n_ner / (len(qa) + n_ner) <= ratio  =>  n_ner <= ratio*len(qa)/(1-ratio)
    cap = int(len(qa_rows) * ratio / (1 - ratio)) if ratio < 1 else len(ner_rows)
    keep = ner_rows if len(ner_rows) <= cap else rng.sample(ner_rows, cap)
    rows = qa_rows + keep
    rng.shuffle(rows)
    return rows, len(ner_rows) - len(keep)


def backup(path: Path, stamp: str) -> None:
    """Sao lưu tập cũ. train.jsonl hiện tại là tập copy 90% - vẫn cần giữ để
    đối chiếu copy-rate trước/sau, đừng ghi đè mất."""
    if path.exists():
        dest = path.with_suffix(f".jsonl.bak-{stamp}")
        shutil.copy2(path, dest)
        print(f"  sao lưu {path.name} -> {dest.name}")


def report(label: str, rows: list[dict], dropped_ner: int) -> None:
    c = Counter(kind(r) for r in rows)
    total = len(rows) or 1
    print(f"  {label}: {len(rows):>3} mẫu | "
          f"qa {c['qa']} ({c['qa'] / total:.0%}), "
          f"refusal {c['refusal']} ({c['refusal'] / total:.0%}), "
          f"ner {c['ner']} ({c['ner'] / total:.0%})"
          + (f" | bỏ {dropped_ner} NER quá tỉ lệ" if dropped_ner else ""))


def main() -> None:
    ap = argparse.ArgumentParser(description="Gộp file _v3 thành train.jsonl/valid.jsonl.")
    ap.add_argument("--ner-ratio", type=float, default=NER_RATIO,
                    help=f"tỉ lệ mẫu NER tối đa trong tập (mặc định {NER_RATIO})")
    ap.add_argument("--dry-run", action="store_true", help="chỉ in thành phần, không ghi file")
    args = ap.parse_args()

    if not 0 <= args.ner_ratio < 1:
        print("ERROR: --ner-ratio phải trong [0, 1).")
        sys.exit(1)

    rng = random.Random(SEED)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    plan = [
        ("Train", DATA / "train_v3.jsonl", DATA / "ner_train_v3.jsonl", DATA / "train.jsonl"),
        ("Valid", DATA / "valid_v3.jsonl", DATA / "ner_valid_v3.jsonl", DATA / "valid.jsonl"),
    ]

    print(f"=== Gộp NER vào tập QA (tỉ lệ NER tối đa {args.ner_ratio:.0%}) ===")
    results: list[tuple[str, list[dict], Path]] = []
    for label, qa_path, ner_path, out_path in plan:
        rows, dropped = compose(read_jsonl(qa_path), read_jsonl(ner_path), args.ner_ratio, rng)
        report(label, rows, dropped)
        results.append((label, rows, out_path))

    if args.dry_run:
        print("\n--dry-run: không ghi file nào.")
        return

    print("\n=== Ghi file ===")
    for _, rows, out_path in results:
        backup(out_path, stamp)
        write_jsonl(out_path, rows)
        print(f"  {out_path}  ({len(rows)} mẫu)")

    n_train = len(results[0][1])
    # 3 epoch, không phải 10. Lần train đầu chạy 1200 iter trên 235 mẫu (~10
    # epoch) và train loss về 0.001 - quá điểm model còn học được gì.
    iters = max(n_train * 3 // 2, 100)
    print(f"\n  Đặt trong training/lora_config.yaml: iters: {iters}   "
          f"(batch_size 2, grad_accum 4 -> ~3 epoch trên {n_train} mẫu)")
    print("  Rồi: bash training/train.sh --fresh")
    print("  ĐỪNG resume: models/lora-adapter/ đang chứa adapter đã học copy.")


if __name__ == "__main__":
    main()
