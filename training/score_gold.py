#!/usr/bin/env python3
"""
Đánh giá 4 metric chính trên gold set:
  1. NER F1 (theo 4 loại: người, địa điểm, sự kiện, thời gian)
  2. Citation Precision: trong các citation model đưa ra, bao nhiêu % có trong nguồn
  3. Refusal Accuracy: câu hỏi ngoài nguồn → model có từ chối đúng không
  4. Style Score: đánh giá tay 1-5 cho văn phong kể chuyện

Các nguyên tắc để số đo có nghĩa:
- Prompt lấy từ backend/core/prompt.py và đi qua chat template của tokenizer.
- Load model MỘT lần bằng Transformers + PEFT, đúng adapter do trainer sinh ra.
- NER dùng micro-F1 (gộp tp/fp/fn) thay vì trung bình F1 từng mẫu. Bản cũ tính
  1.0 cho mẫu mà cả pred và gold đều rỗng, nên loại entity nào hiếm trong corpus
  (ví dụ "sự kiện") được cộng điểm miễn phí và ĐẨY macro-F1 lên giả tạo.

Gold set format (JSONL):
  {"id": "001", "task": "ner", "input": "...", "expected": {...}}
  {"id": "002", "task": "qa", "input": "...", "source": "...", "expected_citations": ["..."]}
  {"id": "003", "task": "refusal", "input": "...", "expected_refusal": true}

Usage:
  # Đo model đang SERVE (base + adapter, đúng thứ backend dùng)
  python training/score_gold.py \
    --gold ./eval/gold.jsonl --out ./eval/report_lora.json

  # Đo base để so sánh
  python training/score_gold.py --base \
    --gold ./eval/gold.jsonl --out ./eval/report_base.json

  # Đo một checkpoint cụ thể
  python training/score_gold.py --adapter models/peft-adapter \
    --checkpoint 75 --gold ./eval/gold.jsonl --out ./eval/report_ck75.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.core.corpus import load_docs  # noqa: E402
from backend.core.prompt import NER_QUESTION, NER_TYPES, SYSTEM, chat_messages  # noqa: E402
from training.train_hf import load_config  # noqa: E402

TRAIN_CONFIG = ROOT / "training" / "lora_config.yaml"
DEFAULT_TRAINING_CONFIG = load_config(TRAIN_CONFIG)
BASE_MODEL = str(DEFAULT_TRAINING_CONFIG["model_id"])
DEFAULT_ADAPTER_PATH = Path(DEFAULT_TRAINING_CONFIG["output_dir"])


def file_identity(path: Path) -> dict[str, str | int]:
    """Return the stable content identity used by reproducibility metadata."""
    content = path.read_bytes()
    return {
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
    }


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def adapter_identity(
    adapter_path: Path,
    explicit_checkpoint: str | None,
) -> dict[str, Any]:
    checkpoint_file = adapter_path / "CHECKPOINT"
    checkpoint = explicit_checkpoint
    if checkpoint is None and checkpoint_file.exists():
        checkpoint = checkpoint_file.read_text("utf-8").strip() or None

    selected_path = adapter_path
    if explicit_checkpoint:
        checkpoint = explicit_checkpoint.removeprefix("checkpoint-")
        checkpoint = f"checkpoint-{checkpoint}"
        selected_path = adapter_path / checkpoint
    weights_path = selected_path / "adapter_model.safetensors"
    return {
        "path": _display_path(selected_path),
        "checkpoint": checkpoint or "best",
        "weights": file_identity(weights_path),
    }


def _git_metadata() -> dict[str, str | bool]:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()

    try:
        return {
            "revision": git("rev-parse", "HEAD"),
            "dirty": bool(git("status", "--porcelain")),
        }
    except (OSError, subprocess.CalledProcessError):
        return {"revision": "unknown", "dirty": True}


def _corpus_identity() -> dict[str, str | int]:
    docs, skipped = load_docs()
    serialized = json.dumps(
        docs, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "sha256": hashlib.sha256(serialized).hexdigest(),
        "documents": len(docs),
        "chunks": sum(len(doc["chunks"]) for doc in docs),
        "skipped_documents": len(skipped),
    }


# ---------- 1. NER F1 ----------

def _as_list(v: object) -> list[str]:
    """Nhận cả list và STRING.

    Model base rất hay trả `{"người": "Gia Long"}` thay vì `["Gia Long"]`. Nếu coi
    string là iterable thì nó bị tách thành từng KÝ TỰ - base bị đo ra F1 = 0.0 vì
    lỗi của scorer, không phải vì trích sai. So base vs LoRA khi đó là gian lận.
    """
    if v is None:
        return []
    if isinstance(v, str):
        return [v.strip()] if v.strip() else []
    if isinstance(v, (list, tuple, set)):
        return [str(x).strip() for x in v if str(x).strip()]
    return [str(v).strip()]


def parse_ner_output(text: str) -> dict[str, list[str]]:
    """Parse JSON từ model output; fallback rỗng nếu model không trả JSON hợp lệ."""
    empty: dict[str, list[str]] = {t: [] for t in NER_TYPES}
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return empty
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return empty
    if not isinstance(obj, dict):
        return empty
    return {t: _as_list(obj.get(t)) for t in NER_TYPES}


def _norm(names: list[str]) -> set[str]:
    return {x.strip().lower() for x in names if x.strip()}


def confusion(pred: list[str], gold: list[str]) -> tuple[int, int, int]:
    """(tp, fp, fn) của một mẫu, một loại entity. Cả hai rỗng -> (0, 0, 0)."""
    pset, gset = _norm(pred), _norm(gold)
    return len(pset & gset), len(pset - gset), len(gset - pset)


def prf(tp: int, fp: int, fn: int) -> dict[str, float | int]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {
        "precision": round(p, 4),
        "recall": round(r, 4),
        "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0,
        "n_gold": tp + fn,
        "n_pred": tp + fp,
    }


# ---------- 2. Citation Precision ----------

def extract_citations(text: str) -> list[str]:
    """Tìm các marker trích dẫn: [Nguồn: ...], (Nguồn ...), v.v."""
    patterns = [
        r"\[Nguồn:\s*([^\]]+)\]",
        r"\(Nguồn:\s*([^)]+)\)",
        r"Nguồn:\s*([^\n\.]+)",
    ]
    out: list[str] = []
    for pat in patterns:
        out.extend(m.strip() for m in re.findall(pat, text))
    return out


# SYSTEM yêu cầu định dạng "[Nguồn: <câu nguyên văn> — <url>]". Phần url không nằm
# trong nguồn nên phải bỏ trước khi khớp, nếu không citation nào cũng bị tính sai.
_URL_TAIL = re.compile(r"\s*[—–-]\s*https?://\S+\s*$")


def citation_precision(pred_cites: list[str], source: str) -> float | None:
    """% citation có thật sự xuất hiện trong source (substring, case-insensitive).

    Trả None khi model KHÔNG trích dẫn gì. Bản cũ trả 1.0 ("không cite = không
    sai"), nên model base - không trích dẫn lần nào trong 9 mẫu - đo ra citation
    precision 1.0, cao bằng model hoàn hảo. Tỉ lệ có trích dẫn được đo riêng ở
    citation_rate, và số để đưa vào báo cáo là citation_faithful_rate.
    """
    if not pred_cites:
        return None
    src_lower = source.lower()
    hit = sum(1 for c in pred_cites if _URL_TAIL.sub("", c).lower() in src_lower)
    return hit / len(pred_cites)


# ---------- 3. Refusal Accuracy ----------

REFUSAL_MARKERS = [
    "không tìm thấy",
    "không có thông tin",
    "ngoài phạm vi",
    "không được cung cấp",
    "không đủ thông tin",
    "không đề cập",
    "xin phép không",
    "không có nội dung nào",
    # Bốn cách nói dưới đây là cách adapter hiện tại từ chối, đo được trên
    # eval/gold.jsonl: 3/15 mẫu bị tính SAI chỉ vì danh sách marker không có chúng
    # ("Nguồn này không chứa thông tin cần tìm", "không có căn cứ để trả lời").
    # Đây là lỗi của scorer, không phải của model - refusal accuracy đo ra 0.73
    # trong khi model thực sự từ chối đúng.
    "không chứa thông tin",
    "không chứa nội dung",
    "không có căn cứ",
    "bổ sung tài liệu",
    "bổ sung tư liệu",
]


def is_refusal(text: str) -> bool:
    t = text.lower()
    return any(m in t for m in REFUSAL_MARKERS)


# ---------- Driver ----------

def load_model(path: str, adapter: str | None = None):
    """Load Hugging Face base model and optional PEFT adapter once."""
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(path, use_fast=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    kwargs: dict[str, Any] = {"device_map": "auto"}
    if torch.cuda.is_available():
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        kwargs["torch_dtype"] = dtype
    else:
        kwargs["torch_dtype"] = torch.float32
    model = AutoModelForCausalLM.from_pretrained(path, **kwargs)
    if adapter:
        model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    return model, tokenizer


def build_messages(sample: dict[str, Any]) -> list[dict[str, str]]:
    """Build the same messages used by serving and training."""
    if sample["task"] == "ner":
        source, question = "", NER_QUESTION.format(text=sample["input"])
    else:
        source, question = sample.get("source", ""), sample["input"]
    return chat_messages(source, question)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=BASE_MODEL,
                    help=f"base model hoặc thư mục model đã fuse (mặc định {BASE_MODEL})")
    ap.add_argument("--adapter", default=str(DEFAULT_ADAPTER_PATH),
                    help="thư mục PEFT adapter; mặc định lấy từ lora_config.yaml")
    ap.add_argument("--checkpoint", default=None,
                    help="iter cụ thể trong --adapter, ví dụ 0000300")
    ap.add_argument("--base", action="store_true",
                    help="chạy base, KHÔNG gắn adapter (để lấy cột so sánh)")
    ap.add_argument("--gold", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--max-tokens", type=int, default=768)
    args = ap.parse_args()

    adapter: str | None = None
    adapter_meta: dict[str, Any] | None = None
    if not args.base:
        adapter_meta = adapter_identity(Path(args.adapter), args.checkpoint)
        adapter = str(ROOT / adapter_meta["path"])
    print(f"model: {args.model}  adapter: {adapter or '(không)'}", file=sys.stderr)

    samples = [json.loads(l) for l in args.gold.read_text("utf-8").splitlines() if l.strip()]

    model, tokenizer = load_model(args.model, adapter)

    conf: dict[str, list[int]] = {t: [0, 0, 0] for t in NER_TYPES}
    cite_scores: list[float] = []
    n_qa = 0
    n_faithful = 0
    refusal_correct = 0
    refusal_total = 0
    style_samples: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []

    for i, s in enumerate(samples, 1):
        messages = build_messages(s)
        print(f"[{i}/{len(samples)}] task={s['task']} id={s.get('id','')}", file=sys.stderr)
        # NER chỉ cần một object JSON ngắn; cắt bớt token để đỡ chờ.
        cap = 256 if s["task"] == "ner" else args.max_tokens
        inputs = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_tensors="pt",
            return_dict=True,
        ).to(model.device)
        generated = model.generate(
            **inputs,
            max_new_tokens=cap,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
        )
        new_tokens = generated[0, inputs["input_ids"].shape[1]:]
        out = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        outputs.append({"id": s.get("id"), "task": s["task"], "output": out})

        if s["task"] == "ner":
            pred = parse_ner_output(out)
            gold = s["expected"]
            for cat in NER_TYPES:
                tp, fp, fn = confusion(pred[cat], list(gold.get(cat, [])))
                conf[cat][0] += tp
                conf[cat][1] += fp
                conf[cat][2] += fn

        elif s["task"] == "qa":
            cites = extract_citations(out)
            n_qa += 1
            p = citation_precision(cites, s.get("source", ""))
            if p is not None:
                cite_scores.append(p)
                if p == 1.0:
                    n_faithful += 1
            style_samples.append({"id": s.get("id"), "input": s["input"], "output": out})

        elif s["task"] == "refusal":
            refusal_total += 1
            if bool(s.get("expected_refusal", False)) == is_refusal(out):
                refusal_correct += 1

    tot = [sum(c[k] for c in conf.values()) for k in range(3)]
    citation_coverage = (len(cite_scores) / n_qa) if n_qa else None
    report = {
        "model": args.model,
        "adapter": adapter_meta["path"] if adapter_meta else None,
        "checkpoint": adapter_meta["checkpoint"] if adapter_meta else None,
        "n_samples": len(samples),
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git": _git_metadata(),
            "gold": {"path": _display_path(args.gold), **file_identity(args.gold)},
            "prompt": {
                "path": "backend/core/prompt.py",
                **file_identity(ROOT / "backend" / "core" / "prompt.py"),
                "system_sha256": hashlib.sha256(SYSTEM.encode("utf-8")).hexdigest(),
            },
            "corpus": _corpus_identity(),
            "scorer": {
                "path": "training/score_gold.py",
                **file_identity(Path(__file__)),
            },
            "adapter": adapter_meta,
            "generation": {
                "sampler": "greedy",
                "temperature": 0.0,
                "max_tokens": args.max_tokens,
                "ner_max_tokens": 256,
            },
        },
        "ner_by_type": {t: prf(*conf[t]) for t in NER_TYPES},
        "ner_micro": prf(*tot),
        # Số để đưa vào báo cáo: bao nhiêu % câu trả lời CÓ trích dẫn và MỌI trích
        # dẫn đều là chuỗi có thật trong nguồn. Không trích dẫn cũng là sai.
        "citation_faithful_rate": (n_faithful / n_qa) if n_qa else None,
        "citation_coverage": citation_coverage,
        "citation_rate": citation_coverage,
        "citation_precision_when_cited": (
            sum(cite_scores) / len(cite_scores)) if cite_scores else None,
        "n_citation_samples": n_qa,
        "refusal_accuracy": (refusal_correct / refusal_total) if refusal_total else None,
        "n_refusal_samples": refusal_total,
        "style_samples_pending_manual": style_samples,
        "raw_outputs": outputs,
    }
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")

    # In gọn: raw_outputs dài, chỉ nằm trong file.
    summary = {k: v for k, v in report.items()
               if k not in ("style_samples_pending_manual", "raw_outputs")}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nStyle: {len(style_samples)} mẫu chờ chấm tay 1-5 "
          f"(tính kể chuyện / trang trọng / tự nhiên) trong {args.out}", file=sys.stderr)
    for t in NER_TYPES:
        if conf[t][0] + conf[t][2] < 5:
            print(f"CẢNH BÁO: loại {t!r} chỉ có {conf[t][0] + conf[t][2]} entity trong gold "
                  f"- F1 của loại này không đủ mẫu để tin.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
