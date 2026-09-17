#!/usr/bin/env python3
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

from backend.core.corpus import INDEX_FILE, load_docs  # noqa: E402
from backend.core.prompt import SYSTEM, user_msg  # noqa: E402
from training.bootstrap_deep_qa import (  # noqa: E402
    DEFAULT_TEACHER,
    NO_SOURCE_QUESTIONS,
    SEED,
    VALID_EVERY,
    count_refusals,
    dedupe,
    drop_leaked,
    faithful,
    intents_for,
    make_ner_samples,
    make_no_source_samples,
    make_off_topic_samples,
    make_quote,
    make_wrong_doc_samples,
    ner_type_coverage,
    pick_chunk,
    pick_sentences,
    split_docs,
    teacher_generate,
    write_jsonl,
)

# Ghi ra file _v3 để tập cũ còn nguyên mà đối chiếu. Đổi tên trong lora_config.yaml
# (hoặc mv sang train.jsonl) khi đã xem báo cáo copy-rate và thấy đạt.
OUT_TRAIN = ROOT / "data" / "train_v3.jsonl"
OUT_VALID = ROOT / "data" / "valid_v3.jsonl"
OUT_NER_TRAIN = ROOT / "data" / "ner_train_v3.jsonl"
OUT_NER_VALID = ROOT / "data" / "ner_valid_v3.jsonl"

# Số TỪ liên tiếp tối đa được phép trùng nguyên văn với nguồn. 14 vì cụm cố định
# trong tiếng Việt di sản dài sẵn: "được UNESCO công nhận là Di sản văn hóa phi
# vật thể đại diện của nhân loại" là 15 từ và gần như không có cách nói khác.
# Dưới 10 loại gần hết mẫu đúng; trên 20 thì copy cả mệnh đề vẫn lọt.
MAX_VERBATIM_RUN = 14

NGRAM = 9           # bậc n-gram dùng để BÁO CÁO tỉ lệ trùng (không dùng để chặn)
MAX_RETRY = 3       # số lần nhờ teacher viết lại trước khi bỏ mẫu
MAX_TOKENS = 420

WORD_RE = re.compile(r"\w+", re.UNICODE)

# --- Đo mức độ sao chép -----------------------------------------------------

def words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def body_of(answer: str) -> str:
    """Bỏ phần [Nguồn: ...] trước khi đo: chỗ đó BẮT BUỘC verbatim, copy là đúng."""
    return answer.split("[Nguồn:")[0].strip()


def longest_common_run(a: list[str], b: list[str]) -> tuple[int, int]:
    """Chuỗi từ liên tiếp dài nhất có ở cả a và b -> (độ dài, vị trí kết trong a).

    DP một hàng. Nguồn ~250 từ, câu trả lời ~150 từ nên O(n*m) là đủ nhanh.
    """
    if not a or not b:
        return 0, 0
    prev = [0] * (len(b) + 1)
    best = best_end = 0
    for i, wa in enumerate(a, 1):
        cur = [0] * (len(b) + 1)
        for j, wb in enumerate(b, 1):
            if wa == wb:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best, best_end = cur[j], i
        prev = cur
    return best, best_end


def ngram_overlap(a: list[str], b: list[str], n: int = NGRAM) -> float:
    """Tỉ lệ n-gram của a cũng xuất hiện trong b. 0 = viết lại hẳn, 1 = copy."""
    if len(a) < n:
        return 0.0
    grams = [tuple(a[i:i + n]) for i in range(len(a) - n + 1)]
    pool = {tuple(b[i:i + n]) for i in range(max(len(b) - n + 1, 0))}
    return sum(1 for g in grams if g in pool) / len(grams)


def copy_report(answer: str, source: str) -> dict:
    body = words(body_of(answer))
    run, end = longest_common_run(body, words(source))
    return {
        "run": run,
        "overlap": ngram_overlap(body, words(source)),
        "quote": " ".join(body[max(end - run, 0):end]),
        "n_words": len(body),
    }


def copy_reason(answer: str, source: str, max_run: int = MAX_VERBATIM_RUN) -> str:
    """"" nếu thân bài là diễn đạt lại; ngược lại trả lý do để log."""
    rep = copy_report(answer, source)
    if rep["run"] > max_run:
        return f"copy {rep['run']} từ liên tiếp: {rep['quote'][:60]!r}"
    return ""


# --- Teacher ----------------------------------------------------------------

TEACHER_SYSTEM = """Bạn là nhà nghiên cứu văn hóa, đang viết đoạn trả lời cho khách tham quan.

CÁCH VIẾT:
- Đọc tư liệu, hiểu nội dung, rồi TỰ DIỄN ĐẠT LẠI bằng câu của mình.
- TUYỆT ĐỐI KHÔNG sao lại nguyên văn câu nào trong tư liệu. Hãy gộp ý, đổi trật tự, đổi cách nói.
- Gộp các thông tin rời rạc thành một mạch kể liền lạc, giọng trang trọng và tự nhiên.
- Trả lời trực tiếp đúng câu hỏi được đặt ra, khoảng 90-160 từ.

GIỚI HẠN:
- KHÔNG thêm bất kỳ con số, năm, tên người hay tên địa danh nào không có trong tư liệu.
- Không lời chào, không nhận xét cá nhân, không gạch đầu dòng, không trích nguồn.
- Chỉ trả về đúng một đoạn văn."""

RETRY_NOTE = ("\n\nLƯU Ý: bản viết trước của bạn còn sao nguyên văn tư liệu. "
              "Lần này hãy diễn đạt lại HOÀN TOÀN bằng câu của bạn.")


def short_reason(reason: str) -> str:
    """Gom lý do của faithful() về vài nhóm để bảng thống kê đọc được."""
    if reason.startswith("tên "):
        return "bỏ: thêm tên không có trong nguồn"
    if reason.startswith("số "):
        return "bỏ: thêm số không có trong nguồn"
    return f"bỏ: {reason}"


def rewrite(model_path: str, name: str, question: str, sents: list[str],
            chunk_text: str, stats: Counter, max_run: int) -> str | None:
    """Nhờ teacher viết lại; phải qua CẢ HAI cổng mới nhận, fail thì bỏ mẫu.

    Cổng 1 (faithful, dùng lại của bootstrap_deep_qa): không thêm số/tên ngoài
    tư liệu, không đi từ chối. Đo trên đúng các câu đã đưa cho teacher.
    Cổng 2 (copy_reason): không sao nguyên văn. Đo trên TOÀN BỘ chunk, vì lúc
    serve model nhìn thấy cả chunk nên copy bất cứ đoạn nào trong đó cũng là copy.

    Không có nhánh fallback extractive: thà ít mẫu còn hơn dạy model copy.
    """
    given = " ".join(sents)

    for attempt in range(MAX_RETRY):
        messages = [
            {"role": "system", "content": TEACHER_SYSTEM + (RETRY_NOTE if attempt else "")},
            {"role": "user", "content": f"Câu hỏi cần trả lời: {question}\n\nTư liệu:\n{given}"},
        ]
        # temp tăng dần: ở temp=0 model bám sát cú pháp nguồn nên hay copy; cần
        # thêm tự do để nó thực sự viết lại, cổng trung thực vẫn giữ nó trong nguồn.
        try:
            text = teacher_generate(
                model_path,
                messages,
                max_tokens=MAX_TOKENS,
                temperature=0.3 + 0.3 * attempt,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"    [WARN] teacher lỗi: {exc}")
            stats["bỏ: lỗi teacher"] += 1
            return None

        text = (text or "").strip()
        reason = faithful(text, given, allow=(name,))
        if reason:
            stats[short_reason(reason)] += 1
            continue
        reason = copy_reason(text, chunk_text, max_run)
        if reason:
            stats["bỏ: copy nguyên văn"] += 1
            continue
        stats[f"nhận (lần thử {attempt + 1})"] += 1
        return text

    return None


# --- Sinh mẫu ---------------------------------------------------------------

def qa_for_doc(doc: dict, teacher: str, stats: Counter,
               max_run: int) -> tuple[list[dict], list[str]]:
    samples: list[dict] = []
    dropped: list[str] = []
    used: set[int] = set()

    for intent in intents_for(doc["category"]):
        picked = pick_chunk(doc["chunks"], used, intent)
        if picked is None:
            dropped.append(f"{intent['id']}: chunk không đủ liên quan")
            continue
        idx, chunk = picked
        used.add(idx)
        question = intent["q"].format(name=doc["name"])
        sents = pick_sentences(chunk, intent["kw"])
        if not sents:
            dropped.append(f"{intent['id']}: không chọn được câu")
            continue

        body = rewrite(teacher, doc["name"], question, sents, chunk["text"], stats, max_run)
        if body is None:
            dropped.append(f"{intent['id']}: không qua cổng")
            continue

        # Trích dẫn vẫn do script ghép: định dạng luôn đúng và câu trích luôn là
        # chuỗi CÓ THẬT trong chunk. Đây là phần duy nhất được phép verbatim.
        quote = make_quote(chunk, sents, intent["kw"])
        samples.append({"messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_msg(chunk["text"], question)},
            {"role": "assistant", "content": f"{body} [Nguồn: {quote} — {doc['url']}]"},
        ]})
    return samples, dropped


def build_split(docs: list[dict], no_source_qs: list[str], rng: random.Random,
                teacher: str, stats: Counter, max_run: int) -> tuple[list[dict], list[dict]]:
    """-> (mẫu QA + refusal, mẫu NER). NER trả riêng để ghi ra file riêng."""
    qa: list[dict] = []
    for doc in docs:
        got, dropped = qa_for_doc(doc, teacher, stats, max_run)
        qa.extend(got)
        note = f"   bỏ {len(dropped)}: {'; '.join(dropped)}" if dropped else ""
        print(f"  {doc['name']:<32} {len(got):>2} mẫu{note}", flush=True)

    # Refusal giữ nguyên template: câu từ chối ĐÚNG là hành vi an toàn cần lặp
    # lại y nguyên, không phải chỗ cần đa dạng văn phong. Đây cũng là phần duy
    # nhất mà model học thuộc là điều mong muốn.
    refusal = (make_no_source_samples(rng, no_source_qs)
               + make_off_topic_samples(rng, docs)
               + make_wrong_doc_samples(rng, docs))
    print(f"  + refusal {len(refusal):>3} mẫu (giữ template - có chủ ý)")

    ner = make_ner_samples(rng, docs)
    print(f"  + NER     {len(ner):>3} mẫu (ghi file riêng, không trộn vào QA)")

    rows = qa + refusal
    rng.shuffle(rows)
    rng.shuffle(ner)
    return rows, ner


# --- Audit -------------------------------------------------------------------

def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def source_text(row: dict) -> str:
    head = row["messages"][1]["content"].split("\n\nCâu hỏi:")[0]
    return head[len("Nguồn: "):] if head.startswith("Nguồn: ") else head


def audit(rows: list[dict], label: str, max_run: int = MAX_VERBATIM_RUN) -> None:
    """Báo cáo copy-rate của một tập dữ liệu.

    Chạy cái này trên tập cũ và tập mới để so. Không có chỉ số này thì lỗi copy
    hoàn toàn vô hình: val loss 0.163 trông rất đẹp trong khi model chỉ photocopy.
    """
    reps: list[tuple[dict, str]] = []
    n_ner = n_refusal = 0
    for row in rows:
        answer = row["messages"][-1]["content"]
        if answer.lstrip().startswith("{"):
            n_ner += 1
            continue
        if "[Nguồn:" not in answer:
            n_refusal += 1
            continue
        reps.append((copy_report(answer, source_text(row)), answer))

    print(f"\n=== Copy-rate: {label} ===")
    print(f"  {len(rows)} mẫu | {len(reps)} QA có trích dẫn | "
          f"{n_ner} NER, {n_refusal} refusal (không tính)")
    if not reps:
        return

    runs = sorted(r["run"] for r, _ in reps)
    overlaps = [r["overlap"] for r, _ in reps]
    over = [x for x in runs if x > max_run]
    print(f"  chuỗi từ trùng nguyên văn dài nhất: trung vị {runs[len(runs) // 2]}, "
          f"tối đa {runs[-1]}")
    print(f"  vượt ngưỡng {max_run} từ: {len(over)}/{len(reps)} ({len(over) / len(reps):.0%})")
    print(f"  n-gram {NGRAM} trùng nguồn (0 = viết lại hẳn): "
          f"trung bình {sum(overlaps) / len(overlaps):.1%}")
    worst = sorted(reps, key=lambda t: -t[0]["run"])[:3]
    if worst and worst[0][0]["run"] > max_run:
        print("  3 mẫu copy nhiều nhất:")
        for rep, _ in worst:
            print(f"    {rep['run']:>3} từ  {rep['quote'][:74]!r}")


def summarize(label: str, rows: list[dict], path: Path) -> None:
    ref = count_refusals(rows)
    pct = f"{ref / len(rows):.0%}" if rows else "0%"
    print(f"  {label}: {len(rows):>3} mẫu | {ref} refusal ({pct})  → {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sinh training data abstractive (chống copy).")
    parser.add_argument("--audit", metavar="FILE",
                        help="chỉ đo copy-rate của một file .jsonl rồi thoát")
    parser.add_argument("--model", default=DEFAULT_TEACHER,
                        help=f"model teacher, phải là model GỐC (mặc định: {DEFAULT_TEACHER})")
    parser.add_argument("--max-run", type=int, default=MAX_VERBATIM_RUN,
                        help=f"số từ liên tiếp tối đa được trùng nguồn (mặc định {MAX_VERBATIM_RUN})")
    args = parser.parse_args()

    if args.audit:
        path = Path(args.audit)
        if not path.exists():
            print(f"ERROR: không có {path}")
            sys.exit(1)
        audit(read_jsonl(path), path.name, args.max_run)
        return

    # Chặn tự distill: teacher là adapter đã học copy thì mọi mẫu mới sẽ copy
    # tiếp, mà cổng chống copy không phát hiện được vì nó chỉ so với nguồn.
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
    print(f"\n=== Teacher: {args.model} (2 cổng: không bịa + không copy > {args.max_run} từ) ===")
    print("    Mẫu không qua cổng bị BỎ, không có fallback copy nguyên văn.")

    stats: Counter = Counter()
    train_docs, valid_docs = split_docs(docs)
    cut = len(NO_SOURCE_QUESTIONS) * (VALID_EVERY - 1) // VALID_EVERY

    print(f"\n--- TRAIN ({len(train_docs)} địa điểm) ---")
    train_rows, train_ner = build_split(train_docs, NO_SOURCE_QUESTIONS[:cut], rng,
                                        args.model, stats, args.max_run)
    print(f"\n--- VALID ({len(valid_docs)} địa điểm, tách riêng khỏi train) ---")
    valid_rows, valid_ner = build_split(valid_docs, NO_SOURCE_QUESTIONS[cut:], rng,
                                        args.model, stats, args.max_run)

    train_rows, valid_rows = dedupe(train_rows), dedupe(valid_rows)
    leaked = len(valid_rows)
    valid_rows = drop_leaked(valid_rows, train_rows)
    if leaked != len(valid_rows):
        print(f"\n  bỏ {leaked - len(valid_rows)} mẫu valid dùng chung đoạn nguồn với train")

    write_jsonl(OUT_TRAIN, train_rows)
    write_jsonl(OUT_VALID, valid_rows)
    write_jsonl(OUT_NER_TRAIN, dedupe(train_ner))
    write_jsonl(OUT_NER_VALID, dedupe(valid_ner))

    print("\n=== Teacher ===")
    for reason, n in stats.most_common():
        print(f"  {reason:<44} {n}")

    print("\n=== Done ===")
    summarize("Train", train_rows, OUT_TRAIN)
    summarize("Valid", valid_rows, OUT_VALID)
    print(f"  NER  : {len(train_ner):>3} train / {len(valid_ner)} valid  → {OUT_NER_TRAIN.name}, "
          f"{OUT_NER_VALID.name}")
    print(f"         NER phủ theo loại (train): {ner_type_coverage(train_ner)}")

    audit(train_rows, OUT_TRAIN.name, args.max_run)
    audit(valid_rows, OUT_VALID.name, args.max_run)

    # 3 epoch, không phải 10. Lần trước 1200 iter trên 235 mẫu đưa train loss về
    # 0.001 - quá điểm model còn học được gì. Dừng theo val loss, đừng chạy hết.
    print(f"\n  Gợi ý iters cho lora_config.yaml (batch_size 2, ~3 epoch): "
          f"{max(len(train_rows) * 3 // 2, 100)}")
    print("  Nhớ: train --fresh, ĐỪNG resume trên adapter cũ đã học copy.")


if __name__ == "__main__":
    main()
