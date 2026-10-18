"""Endpoint xem knowledge graph - KHÔNG gọi LLM, nên gọi được cả khi chưa fuse model.

Có ba việc:
  GET /api/graph/stats               - số liệu tổng quan
  GET /api/graph/subgraph?node=Huế   - node + láng giềng, dạng node-link để frontend vẽ
  GET /api/graph/trace?q=...         - TRUY DẤU: câu hỏi neo vào node nào, graph
                                       cộng thêm bao nhiêu điểm, có ra context không
`trace` là thứ để trả lời câu "graph có tác dụng gì": nó cho thấy điểm graph và
lý do một chunk được chọn, tách khỏi điểm lexical.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from apps.backend.core.kg import expand_docs, find_seeds, graph_stats
from apps.backend.core.rag import retrieve_context
from apps.backend.core.retriever import get_retriever

router = APIRouter(prefix="/graph", tags=["graph"])

MAX_NEIGHBORS = 60


@router.get("/stats")
def stats() -> dict:
    r = get_retriever()
    st = graph_stats(r.graph)
    st["chunks"] = len(r.chunks)
    return st


@router.get("/subgraph")
def subgraph(
    node: str = Query(..., description="nhãn node, ví dụ 'Huế' hay 'lăng Tự Đức'"),
    hops: int = Query(1, ge=1, le=2),
) -> dict:
    G = get_retriever().graph
    low = node.lower()
    ids = [n for n, d in G.nodes(data=True) if d.get("label", "").lower() == low]
    if not ids:
        ids = [n for n, d in G.nodes(data=True) if low in d.get("label", "").lower()]
    if not ids:
        raise HTTPException(status_code=404, detail=f"không có node nào tên {node!r}")

    keep = set(ids[:5])
    for _ in range(hops):
        for n in list(keep):
            nbrs = sorted(G.neighbors(n), key=lambda m: -G[n][m].get("weight", 1.0))
            keep.update(nbrs[:MAX_NEIGHBORS])

    return {
        "nodes": [
            {"id": n, "label": G.nodes[n].get("label", n), "kind": G.nodes[n].get("kind"),
             "degree": G.degree(n), "seed": n in ids}
            for n in keep
        ],
        "links": [
            {"source": a, "target": b, "rel": d.get("rel"), "weight": d.get("weight", 1.0)}
            for a, b, d in G.subgraph(keep).edges(data=True)
        ],
    }


@router.get("/trace")
def trace(q: str = Query(..., min_length=1), top_k: int = Query(5, ge=1, le=20)) -> dict:
    r = get_retriever()
    G = r.graph
    seeds = find_seeds(G, q)
    res = r.retrieve(q, top_k=top_k)
    context, _ = retrieve_context(q)
    return {
        "query": q,
        "anchored": res["anchored"],
        "seeds": [
            {"label": G.nodes[s]["label"], "kind": G.nodes[s].get("kind"), "degree": G.degree(s)}
            for s in seeds
        ],
        "specific": res["specific"],
        "named_docs": res["named"],
        "expanded_docs": sorted(
            ({"doc": G.nodes[dn]["label"], "graph_score": round(sc, 3)}
             for dn, sc in expand_docs(G, seeds).items()),
            key=lambda d: -d["graph_score"],
        )[:10],
        "hits": [
            {"chunk_id": h["chunk_id"], "doc": h["doc"], "heading": h["heading"],
             "score": h["score"], "lexical": h["lexical"], "graph": h["graph"],
             "named": h["named"], "coverage": h["coverage"], "graph_hits": h["graph_hits"]}
            for h in res["hits"]
        ],
        # rỗng = cổng từ chối đã chặn; llm.py sẽ ghi "Nguồn: (không có)"
        "context_chars": len(context),
        "will_refuse": not context,
    }
