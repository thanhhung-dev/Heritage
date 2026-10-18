#!/usr/bin/env python3
"""Xây + XEM knowledge graph. Không gọi LLM, không cần mạng, chạy ~0.5 giây.

Ba chế độ:
  build_graph.py                 - thống kê graph + xuất artifact ra graphrag/output/
  build_graph.py --query "..."   - TRUY DẤU: câu hỏi neo vào node nào, lan ra bài nào,
                                   graph cộng thêm bao nhiêu điểm cho từng chunk
  build_graph.py --node "Huế"    - xem một node: láng giềng và quan hệ

Artifact xuất ra:
  graph.gexf   - mở bằng Gephi để nhìn cả đồ thị
  graph.json   - node-link JSON, cho frontend vẽ (D3/cytoscape)
  stats.json   - số liệu để đưa vào docs/báo cáo

Chạy: apps/backend/.venv/bin/python pipelines/graph/build_graph.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import networkx as nx  # noqa: E402

from apps.backend.core.config import PROJECT_ROOT       # noqa: E402
from apps.backend.core.corpus import load_docs          # noqa: E402
from apps.backend.core.kg import build_graph, expand_docs, find_seeds, graph_stats  # noqa: E402

OUT_DIR = PROJECT_ROOT / "graphrag" / "output"


def cmd_build(G: nx.Graph, docs: list[dict], skipped: list[tuple[str, str]], secs: float) -> None:
    st = graph_stats(G)
    print(f"corpus : {len(docs)} bài / {sum(len(d['chunks']) for d in docs)} chunk "
          f"({len(skipped)} bài bị bỏ)")
    for name, why in skipped:
        print(f"         - bỏ {name}: {why}")
    print(f"graph  : {st['nodes']} node / {st['edges']} edge / "
          f"{st['components']} thành phần liên thông  ({secs:.2f}s)")
    print(f"  node : {st['by_kind']}")
    print(f"  edge : {st['by_rel']}")
    print("  hub  : " + ", ".join(f"{lb}({dg})" for lb, dg in st["top_hub"]))
    if st["isolated_docs"]:
        print(f"  BÀI GẦN NHƯ CÔ LẬP (graph giúp được rất ít): {st['isolated_docs']}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # GEXF không nhận giá trị None nên ép mọi attr về str/số
    H = nx.Graph()
    for n, d in G.nodes(data=True):
        H.add_node(n, **{k: ("" if v is None else v if isinstance(v, (int, float)) else str(v))
                         for k, v in d.items()})
    for a, b, d in G.edges(data=True):
        H.add_edge(a, b, **{k: (v if isinstance(v, (int, float)) else str(v))
                            for k, v in d.items()})
    nx.write_gexf(H, OUT_DIR / "graph.gexf")
    (OUT_DIR / "graph.json").write_text(
        json.dumps(nx.node_link_data(H, edges="links"), ensure_ascii=False, indent=1), "utf-8")
    (OUT_DIR / "stats.json").write_text(
        json.dumps(st, ensure_ascii=False, indent=2), "utf-8")
    rel = OUT_DIR.relative_to(PROJECT_ROOT)
    print(f"\nĐã xuất: {rel}/graph.gexf, {rel}/graph.json, {rel}/stats.json")


def cmd_query(G: nx.Graph, query: str) -> None:
    from apps.backend.core.rag import retrieve_context
    from apps.backend.core.retriever import get_retriever

    seeds = find_seeds(G, query)
    print(f"câu hỏi : {query}")
    if not seeds:
        print("neo     : (không có) -> ngoài miền tri thức, hệ sẽ từ chối lịch sự")
    for s in seeds:
        d = G.nodes[s]
        print(f"neo     : {d['label']!r} [{d.get('kind')}] bậc={G.degree(s)}")

    doc_scores = expand_docs(G, seeds)
    print("lan toả :" + (" (không có)" if not doc_scores else ""))
    for dn, sc in sorted(doc_scores.items(), key=lambda kv: -kv[1])[:8]:
        print(f"          {sc:.3f}  {G.nodes[dn]['label']}")

    res = get_retriever().retrieve(query, top_k=5)
    print(f"gọi tên : {res['named'] or '(không có)'}   neo cụ thể: {res['specific'] or '(không có)'}")
    print("xếp hạng: (điểm = lexical + graph + entity + gọi-đúng-tên)")
    for h in res["hits"]:
        print(f"          {h['score']:.3f} = lex {h['lexical']:.3f} + graph {h['graph']:.3f}"
              f"{' + TÊN' if h['named'] else '      '}  cov {h['coverage']:.2f}  "
              f"{h['chunk_id']}  hits={h['graph_hits'][:3]}")
    ctx, _ = retrieve_context(query)
    print(f"context : {len(ctx)} ký tự" + ("  -> RỖNG, model sẽ từ chối" if not ctx else ""))
    if ctx:
        print(f"          {ctx[:200]}...")


def cmd_node(G: nx.Graph, label: str) -> None:
    matches = [n for n, d in G.nodes(data=True) if d.get("label", "").lower() == label.lower()]
    if not matches:
        matches = [n for n, d in G.nodes(data=True) if label.lower() in d.get("label", "").lower()]
    if not matches:
        print(f"không có node nào tên {label!r}")
        return
    for n in matches[:5]:
        d = G.nodes[n]
        print(f"\n{n}  [{d.get('kind')}] bậc={G.degree(n)}"
              + ("  (curated)" if d.get("curated") else ""))
        nbrs = sorted(G.neighbors(n), key=lambda m: -G[n][m].get("weight", 1.0))
        for m in nbrs[:15]:
            e = G[n][m]
            print(f"    --{e.get('rel')}({e.get('weight', 1.0):g})--> "
                  f"{G.nodes[m]['label']} [{G.nodes[m].get('kind')}]")
        if len(nbrs) > 15:
            print(f"    ... còn {len(nbrs) - 15} láng giềng")


def main() -> int:
    ap = argparse.ArgumentParser(description="Xây và xem knowledge graph di sản")
    ap.add_argument("--query", help="truy dấu một câu hỏi qua graph")
    ap.add_argument("--node", help="xem láng giềng của một node")
    args = ap.parse_args()

    t0 = time.perf_counter()
    docs, skipped = load_docs()
    G = build_graph(docs)
    secs = time.perf_counter() - t0

    if args.query:
        cmd_query(G, args.query)
    elif args.node:
        cmd_node(G, args.node)
    else:
        cmd_build(G, docs, skipped, secs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
