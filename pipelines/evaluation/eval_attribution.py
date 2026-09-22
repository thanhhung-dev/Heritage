#!/usr/bin/env python3
"""Quy trách nhiệm lỗi retrieval — offline, không cần model, không cần mạng.

eval_retrieval.py trả lời "bao nhiêu câu đúng". Script này trả lời "những câu sai
thì sai vì cái gì", vì đó là con số quyết định làm DATA hay làm KIẾN TRÚC.

Năm nhóm loại trừ nhau, đọc theo thứ tự nhân quả:

  A  KHÔNG CÓ TRONG CORPUS   bài không tồn tại, hoặc bài có mà không chứa dữ kiện.
                             Không thuật toán nào cứu được  ->  làm DATA.
  B  RETRIEVAL               dữ kiện có trong corpus mà không vào được context.
       B_POOL   không vào nổi top-DEEP_K  -> hỏng SINH ỨNG VIÊN (bơm / kênh mới)
       B_RANK   vào pool nhưng không top-1 -> hỏng XẾP HẠNG (rerank)
       B_CHUNK  đúng bài, sai chunk        -> hỏng XẾP HẠNG TẦNG 2
  C  CỔNG CHẶN OAN           context rỗng cho câu hợp lệ -> hiệu chỉnh NGƯỠNG,
                             đừng thêm kênh.
  D  SINH                    context đã đủ bằng chứng; lỗi còn lại thuộc LoRA.
                             KHÔNG đo được ở đây (cần model) — xem ghi chú cuối file.
  E  RÒ                      câu ngoài phạm vi mà context khác rỗng. Cổng quá lỏng.

Quy tắc dùng: nhóm nào chiếm khối lượng lớn nhất thì tuần sau làm nhóm đó. Đừng
thêm kênh vector khi A đang trội — cải thiện sẽ bằng 0 và anh sẽ kết luận SAI rằng
kênh vector vô dụng.

Chạy:
  apps/backend/.venv/bin/python pipelines/evaluation/eval_attribution.py
  apps/backend/.venv/bin/python pipelines/evaluation/eval_attribution.py --update-baseline
  apps/backend/.venv/bin/python pipelines/evaluation/eval_attribution.py --json pipelines/evaluation/runs/2026-09-08.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.backend.core.rag import retrieve_context
from apps.backend.core.retriever import get_retriever
from pipelines.evaluation.eval_retrieval import (
    EVIDENCE, IN_DOMAIN, OUT_OF_DOMAIN, PARAPHRASE, WARD,
)


B_RANK_DUMP = "pipelines/evaluation/b_rank_dump.txt"
DEEP_K = 50
BASELINE_PATH = ROOT / "pipelines" / "evaluation" / "baseline_attribution.json"

ACTION = {
    "A_DOC":   "DATA — crawl/soạn bài còn thiếu",
    "A_FACT":  "DATA — bài có nhưng thiếu dữ kiện, cần nguồn khác",
    "B_POOL":  "KIẾN TRÚC — sinh ứng viên (bơm theo graph / thêm kênh)",
    "B_RANK":  "KIẾN TRÚC — xếp hạng tầng 1 (rerank, trọng số)",
    "B_CHUNK": "KIẾN TRÚC — xếp hạng tầng 2 (chọn chunk trong bài)",
    "C_GATE":  "NGƯỠNG — cổng chặn oan, hiệu chỉnh chứ đừng thêm kênh",
    "E_LEAK":  "NGƯỠNG — cổng quá lỏng, siết lại",
}



def strip_tones(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()


def has_tones(s: str) -> bool:
    nfd = unicodedata.normalize("NFD", s)
    return any(unicodedata.category(c) == "Mn" for c in nfd) or "đ" in s.lower()


def _field(obj, *names):
    """Đọc trường không phụ thuộc chunk là dict hay dataclass.

    Nếu raise ở đây thì chỉ cần thêm tên trường vào lời gọi, không phải sửa gì khác.
    """
    for n in names:
        if isinstance(obj, dict):
            if n in obj:
                return obj[n]
        elif hasattr(obj, n):
            return getattr(obj, n)
    raise KeyError(f"không thấy trường nào trong {names} ở {type(obj).__name__}")


def build_corpus_map(r) -> dict[str, list[str]]:
    """{tên bài: [text của từng chunk]} — dùng để phân biệt nhóm A với nhóm B."""
    docs: dict[str, list[str]] = defaultdict(list)
    for c in r.chunks:
        docs[_field(c, "doc", "doc_title", "title")].append(
            _field(c, "text", "content", "body")
        )
    return dict(docs)


def ranked_docs(r, q: str, k: int) -> tuple[list[str], dict]:
    res = r.retrieve(q, top_k=k)
    order: list[str] = []
    for h in res["hits"]:
        if h["doc"] not in order:
            order.append(h["doc"])
    return order, res


def git_rev() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, timeout=5,
        ).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


# ------------------------------------------------------------------ phân loại

def classify(r, docs, q, gold=None, needle=None, deep_k=DEEP_K):
    """gold: tên bài (str), tập tên bài chấp nhận được (set), hoặc None."""
    golds = None
    if gold is not None:
        golds = {gold} if isinstance(gold, str) else set(gold)

    # A — dữ kiện không có trong corpus. Phải kiểm TRƯỚC retrieval, nếu không thì
    # một bài chưa crawl sẽ hiện ra như lỗi xếp hạng và anh đi tối ưu sai chỗ.
    if golds is not None:
        present = golds & docs.keys()
        if not present:
            return "A_DOC", f"không bài nào trong {sorted(golds)} có trong corpus"
        golds = present

    if needle is not None:
        pool = ([t for g in golds for t in docs[g]] if golds
                else [t for ts in docs.values() for t in ts])
        if not any(needle in t for t in pool):
            where = f"bài {sorted(golds)}" if golds else "toàn corpus"
            return "A_FACT", f"chuỗi {needle!r} không xuất hiện trong {where}"

    order, res = ranked_docs(r, q, deep_k)
    ctx, _, _ = retrieve_context(q)


    print("RANK: ", range)

    # B tầng 1 — chọn bài
    if golds is not None:
        hit_ranks = [order.index(g) for g in golds if g in order]
        if not hit_ranks:
            return "B_POOL", f"không bài nào trong {sorted(golds)} vào top-{deep_k}"
        if order[0] not in golds:
            best = min(hit_ranks) + 1
            with open(B_RANK_DUMP, "a", encoding="utf-8") as f:
                f.write("\n" + "=" * 100 + "\n")
                f.write("B_RANK\n")
                f.write(f"QUERY : {q}\n")
                f.write(f"GOLD  : {gold}\n")
                f.write(f"RANK  : {best}\n")
                f.write(f"TOP-1 : {order[0]!r}\n")
                f.write("-" * 100 + "\n")
                for i, doc in enumerate(order[:50], 1):
                    marker = " <=== GOLD" if doc == gold else ""
                    f.write(f"{i:02d}. {doc}{marker}\n")
                f.write("=" * 100 + "\n")
            return "B_RANK", f"đúng bài ở hạng {best}, top-1 là {order[0]!r}"

    # C — cổng chặn oan (đã chọn đúng bài rồi mà vẫn rỗng)
    if not ctx:
        gate = "anchor" if not res.get("anchored", True) else "evidence/coverage"
        return "C_GATE", f"context rỗng dù bài đúng đứng nhất; cổng nghi vấn: {gate}"

    # B tầng 2 — đúng bài, sai chunk
    if needle is not None and needle not in ctx:
        return "B_CHUNK", f"{needle!r} không có trong context ({len(ctx)} ký tự)"
    return "OK", ""


def classify_ood(r, q):
    ctx, _,_ = retrieve_context(q)
    if not ctx:
        return "OK", ""
    res = r.retrieve(q, top_k=3)
    top = res["hits"][0]["doc"] if res["hits"] else "-"
    return "E_LEAK", (f"rò {len(ctx)} ký tự qua bài {top!r}, "
                      f"anchored={res.get('anchored')}")


def stratum(q: str, gold) -> str:
    """Phân tầng TỰ ĐỘNG, không cần gán nhãn tay — FR12 đòi bảng đo tách kênh."""
    names = [gold] if isinstance(gold, str) else sorted(gold or [])
    qn = strip_tones(q)
    literal = any(strip_tones(n) in qn for n in names)
    return (("có dấu" if has_tones(q) else "không dấu") + " + " +
            ("gọi đúng tên" if literal else "tên khác/diễn giải"))


# --------------------------------------------------------------------- chạy

def evidence_cases():
    """Nhận cả 2-tuple (câu, needle) và 3-tuple (câu, needle, bài) — nâng cấp dần
    EVIDENCE lên 3-tuple thì attribution mới tách được A_FACT theo từng bài."""
    out = []
    for t in EVIDENCE:
        if len(t) == 3:
            q, needle, gold = t
        else:
            q, needle, gold = t[0], t[1], None
        out.append((q, gold, needle))
    return out


def preflight(docs) -> list[str]:
    """Nhãn vàng trỏ vào bài không tồn tại là lỗi CỦA BỘ ĐÁNH GIÁ, không phải của
    hệ. Bắt ở đây, nếu không nó sẽ nằm lẫn trong recall suốt cả kỳ."""
    bad = []
    for q, gold in list(IN_DOMAIN) + list(PARAPHRASE):
        if gold not in docs:
            bad.append(f"{gold!r} (nhãn của {q[:40]!r})")
    for q, gset in WARD:
        for g in gset:
            if g not in docs:
                bad.append(f"{g!r} (nhãn WARD của {q[:40]!r})")
    return sorted(set(bad))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deep-k", type=int, default=DEEP_K)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--show-ok", action="store_true", help="in cả câu đúng")
    args = ap.parse_args()

    r = get_retriever()
    docs = build_corpus_map(r)
    print(f"corpus: {len(r.chunks)} chunk / {len(docs)} bài   deep_k={args.deep_k}   "
          f"rev={git_rev()}\n")

    bad = preflight(docs)
    if bad:
        print("PREFLIGHT HỎNG — nhãn vàng trỏ vào bài không có trong corpus:")
        for b in bad:
            print(f"  - {b}")
        print("\nSửa nhãn hoặc crawl bài, rồi chạy lại. Chưa sửa thì mọi số recall\n"
              "đều đang trừ điểm cho lỗi của bộ đánh giá, không phải của hệ.\n")

    suites = [
        ("TRONG PHẠM VI", [(q, g, None) for q, g in IN_DOMAIN]),
        ("PARAPHRASE",    [(q, g, None) for q, g in PARAPHRASE]),
        ("BẰNG CHỨNG",    evidence_cases()),
        ("PHƯỜNG/XÃ",     [(q, gset, None) for q, gset in WARD]),
    ]

    buckets = Counter()
    strata = defaultdict(lambda: [0, 0])
    per_suite = {}
    records = []

    for name, cases in suites:
        ok = 0
        print(f"== {name} ==")
        for q, gold, needle in cases:
            b, detail = classify(r, docs, q, gold, needle, args.deep_k)
            records.append({"suite": name, "query": q, "bucket": b, "detail": detail})
            if b == "OK":
                ok += 1
                if args.show_ok:
                    print(f"  OK       | {q[:52]}")
            else:
                buckets[b] += 1
                print(f"  {b:8s} | {q[:52]:52s} | {detail}")
            s = stratum(q, gold)
            strata[s][1] += 1
            strata[s][0] += (b == "OK")
        per_suite[name] = {"ok": ok, "total": len(cases)}
        print(f"  -> {ok}/{len(cases)}\n")

    print("== NGOÀI PHẠM VI ==")
    ok = 0
    for q in OUT_OF_DOMAIN:
        b, detail = classify_ood(r, q)
        records.append({"suite": "NGOÀI PHẠM VI", "query": q,
                        "bucket": b, "detail": detail})
        if b == "OK":
            ok += 1
        else:
            buckets[b] += 1
            print(f"  {b:8s} | {q[:52]:52s} | {detail}")
    per_suite["NGOÀI PHẠM VI"] = {"ok": ok, "total": len(OUT_OF_DOMAIN)}
    print(f"  -> {ok}/{len(OUT_OF_DOMAIN)}\n")

    print("== PHÂN TẦNG TRUY VẤN ==")
    for s, (o, t) in sorted(strata.items()):
        print(f"  {o:3d}/{t:3d}  {s}")

    total_err = sum(buckets.values())
    print(f"\n== QUY TRÁCH NHIỆM ({total_err} lỗi) ==")
    if not total_err:
        print("  không có lỗi nào — mở rộng bộ đánh giá, thước đo đang hết độ phân giải")
    for b, n in buckets.most_common():
        print(f"  {n:3d}  {100*n/total_err:5.1f}%  {b:8s}  {ACTION[b]}")
    if total_err:
        top_b = buckets.most_common(1)[0][0]
        print(f"\n  VIỆC TIẾP THEO: {ACTION[top_b]}")
    print("  (nhóm D — model không trung thực với context đã đúng — không đo ở đây)")

    payload = {
        "meta": {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "rev": git_rev(), "deep_k": args.deep_k,
            "chunks": len(r.chunks), "docs": len(docs),
            "preflight_problems": bad,
        },
        "suites": per_suite,
        "buckets": dict(buckets),
        "strata": {k: {"ok": v[0], "total": v[1]} for k, v in strata.items()},
        "records": records,
    }
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"\nđã ghi {args.json}")

    if args.update_baseline:
        BASELINE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"đã cập nhật baseline {BASELINE_PATH.name}")
        return 0

    # Không dùng all-or-nothing: chỉ đỏ khi HỒI QUY so với lần trước. Nhờ vậy một
    # suite baseline đang thấp (paraphrase) không làm exit code mất hết thông tin.
    if not BASELINE_PATH.exists():
        print(f"\nchưa có baseline — chạy --update-baseline để chốt mốc so sánh")
        return 0
    base = json.loads(BASELINE_PATH.read_text())
    regressed = []
    print("\n== SO VỚI BASELINE ==")
    for name, cur in per_suite.items():
        old = base.get("suites", {}).get(name)
        if not old:
            print(f"  {name}: suite mới ({cur['ok']}/{cur['total']})")
            continue
        d = cur["ok"] - old["ok"]
        mark = "  " if d == 0 else ("+" if d > 0 else "!!")
        print(f"  {mark} {name}: {old['ok']}/{old['total']} -> "
              f"{cur['ok']}/{cur['total']} ({d:+d})")
        if d < 0:
            regressed.append(name)
    if regressed:
        print(f"\nHỒI QUY ở: {', '.join(regressed)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
