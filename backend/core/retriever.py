from __future__ import annotations
import os
import math
import re
from collections import defaultdict
from functools import lru_cache
import networkx as nx

from backend.core.corpus import load_docs
from backend.core.kg import build_graph, expand_docs, extract_names, find_seeds, is_admin_name
from backend.core.fuzzy_match import suggest_corrections
from backend.core.textutil import (
    contains_name,
    name_span,
    ngram_tokens,
    strip_accents,
    word_tokens,
)

HEADING_WEIGHT = 3      
RRF_K = 60
GRAPH_WEIGHT = 0.35
NAMED_DOC_BONUS = 0.8   
CHUNK_ENTITY_BONUS = 0.15
CANDIDATES = 30
INJECT_PER_DOC = 5
MIN_FUZZY_SCORE = 0.7

DOC_EVIDENCE_WEIGHTS = (1 , 0.5 , 0.25)

ANCHOR_KINDS = frozenset({"entity", "doc", "region", "category"})


LOCATION_RE = re.compile(
    r"\b(o dau|nam o|toa lac|thuoc tinh|thuoc thanh pho|thuoc dia phan|dia chi"
    r"|vi tri|o tinh|o thanh pho|cach trung tam|o mien|o khu vuc"
    r"|o phuong|o quan|o xa|o huyen|o lang|o thi xa"
    r"|thuoc phuong|thuoc quan|thuoc xa|thuoc huyen|thuoc lang)\b"
)
GENERAL_RE = re.compile(
    r"\b(ke chi tiet|gioi thieu|tong quan|noi ve|chi tiet ve|thong tin ve)\b"
)
TIME_RE = re.compile(
    r"\b(nam nao|khi nao|bao gio|tu nam|vao nam|nam bao nhieu|the ky nao"
    r"|thoi gian nao|nam may)\b"
)

WARD_RE = re.compile(
    r"\b(phuong|quan|xa|huyen|thi xa|thi tran|lang|thon)\s+(nao|gi|may)\b"
    r"|\b(o|tai|thuoc)\s+(phuong|quan|xa|huyen|thi xa|thi tran|lang|thon)\b"
)
VERIFY_RE = re.compile(
    r"\b(dung khong|phai khong|co phai|co dung|dung chu|that khong|phai la)\b"
)

CLAIM_PREFIX_RE = re.compile(
    r"\b(o|tai|thuoc|cua|gan|tren|ben|canh|trong)\s+"
    r"(?:(?:phuong|quan|xa|huyen|tinh|thanh pho|tp|thi xa|thi tran|lang|tong"
    r"|khu|khu vuc|mien|vung|dia phan|dia ban|to dan pho|bo|bo song)\s+)*$"
)

LOCATION_HEADINGS = ("vi tri", "dia ly", "dia diem", "kien tao")

INTENT_HEADING_BONUS = 0.45  
YEAR_IN_CHUNK_RE = re.compile(r"(?<!\d)(1[0-9]{3}|20[0-2][0-9])(?!\d)")


CATEGORY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "Ẩm thực": (
        "mon an", "am thuc", "dac san", "mon ngon", "do an", "mon gi", "an gi", "mon mi",
    ),
    "Lễ hội": ("le hoi", "festival"),
    "Nghệ thuật": ("nghe thuat", "loai hinh dien xuong", "nghe thuat bieu dien"),
    "Làng nghề": ("lang nghe", "nghe truyen thong", "thu cong my nghe"),
    "Danh thắng": ("danh thang", "thang canh", "canh dep"),
    "Di tích lịch sử": ("di tich", "di tich lich su"),
}
REGION_SYNONYMS: dict[str, tuple[str, ...]] = {
    "Huế": ("hue", "thua thien hue", "co do hue"),
    "Đà Nẵng": ("da nang", "danang", "thanh pho bien"),
}



def _flag(name: str, default: bool = True) -> bool:
    return os.environ.get(name, "1" if default else "0") != "0"

TWO_TIER    = _flag("RT_TWO_TIER", default=False)
GATE_AFTER  = _flag("RT_GATE_AFTER")   
FUZZY_UNION = _flag("RT_FUZZY_UNION")   
INJECT_LEAD = _flag("RT_INJECT_LEAD")  

def rank_documents(
    scored_chunks: list[dict],
    doc_graph_scores: dict[str, float],
    named: set[str],
) -> list[dict]:
    by_doc: dict[str, list[float]] = defaultdict(list)
    for c in scored_chunks:
        by_doc[c["doc_node"]].append(c["chunk_score"])

    out: list[dict] = []
    for doc_node, chunk_scores in by_doc.items():
        chunk_scores.sort(reverse=True)
        evidence = sum(
            w * s for w, s in zip(DOC_EVIDENCE_WEIGHTS, chunk_scores)
        )
        g = doc_graph_scores.get(doc_node, 0.0)
        is_named = doc_node in named
        out.append({
            "doc_node": doc_node,
            "doc_score": round(
                evidence + GRAPH_WEIGHT * g + (NAMED_DOC_BONUS if is_named else 0.0), 4
            ),
            "evidence": round(evidence, 4),
            "graph": round(g, 4),
            "named": is_named,
            "n_chunks": len(chunk_scores),
        })
    out.sort(key=lambda d: -d["doc_score"])
    return out




def _match_any(plain_query: str, keys: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(k)}(?!\w)", plain_query) for k in keys)


def query_scope(query: str) -> tuple[str, str]:
    """('Huế', 'Ẩm thực') - chuỗi rỗng nghĩa là KHÔNG giới hạn chiều đó."""
    plain = strip_accents(query)
    region = next((r for r, keys in REGION_SYNONYMS.items() if _match_any(plain, keys)), "")
    category = next((c for c, keys in CATEGORY_SYNONYMS.items() if _match_any(plain, keys)), "")
    return (region, category)


def query_intent(query: str) -> frozenset[str]:
    """{'location'} / {'time'} / {'ward','verify','location'} ... - rỗng nếu không rõ.

    Câu kiểm chứng về di sản gần như luôn kiểm chứng VỊ TRÍ ("X ở Huế đúng
    không"), nên 'verify' kéo theo 'location': bằng chứng cần tìm cùng một chỗ.

    'ward' cũng kéo theo 'location' - nó hẹp hơn, không khác loại - nhưng `rag.py`
    xử lý riêng: xem WARD_RE và `_ensure_ward`.
    """
    q = strip_accents(query)
    found = set()
    if LOCATION_RE.search(q):
        found.add("location")
    if TIME_RE.search(q):
        found.add("time")
    if VERIFY_RE.search(q):
        found.add("verify")
        found.add("location")
    if WARD_RE.search(q):
        found.add("ward")
        found.add("location")
    if GENERAL_RE.search(q):
        found.add("general")
    return frozenset(found)


def is_lead(chunk: dict) -> bool:
    """Đoạn mở đầu bài. Ở corpus wiki nó gần như LUÔN chứa tỉnh/thành."""
    return chunk["chunk_id"].endswith("#0")


def is_admin_chunk(chunk: dict) -> bool:
    """Chunk có nêu đơn vị hành chính cấp phường/xã ('phường Thạch Thang').

    Khác `is_lead`: chỉ 18/45 bài nêu phường trong đoạn mở đầu, số còn lại nêu ở
    giữa bài hoặc không nêu. Dùng để chọn chunk cho câu hỏi cấp phường - xem
    `_ensure_ward` trong rag.py.
    """
    return any(is_admin_name(n) for n in extract_names(chunk["text"]))


def subject_and_claims(query: str, names: list[str]) -> tuple[str, list[str]]:
    if len(names) < 2:
        return ("", [])
    plain = strip_accents(query)
    spans: list[tuple[int, str, bool]] = []
    for name in names:
        span = name_span(plain, name)
        if span is None:
            continue
        spans.append((span[0], name, bool(CLAIM_PREFIX_RE.search(plain[: span[0]]))))
    spans.sort()
    claims = [n for _, n, in_claim in spans if in_claim]
    subject = next((n for _, n, in_claim in spans if not in_claim), "")
    if not subject or not claims:
        return ("", [])
    return (subject, [n for n in claims if n != subject])


class Bm25:
    """BM25 trên inverted index. Tokenizer truyền vào nên dùng lại được cho n-gram."""

    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.n = len(docs)
        self.doc_len = [len(d) for d in docs]
        self.avgdl = (sum(self.doc_len) / self.n) if self.n else 0.0
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for i, toks in enumerate(docs):
            tf: dict[str, int] = defaultdict(int)
            for t in toks:
                tf[t] += 1
            for t, c in tf.items():
                self.postings[t].append((i, c))
        self.idf = {
            t: math.log(1.0 + (self.n - len(p) + 0.5) / (len(p) + 0.5))
            for t, p in self.postings.items()
        }

    def search(self, q_tokens: list[str]) -> dict[int, float]:
        scores: dict[int, float] = defaultdict(float)
        for t in set(q_tokens):
            postings = self.postings.get(t)
            if not postings:
                continue
            idf = self.idf[t]
            for i, tf in postings:
                norm = 1.0 - self.b + self.b * (self.doc_len[i] / (self.avgdl or 1.0))
                scores[i] += idf * tf * (self.k1 + 1.0) / (tf + self.k1 * norm)
        return scores


def _rrf(*rankings: dict[int, float]) -> dict[int, float]:
    """Reciprocal Rank Fusion - hợp nhất theo THỨ HẠNG nên không cần scale điểm."""
    fused: dict[int, float] = defaultdict(float)
    for scores in rankings:
        for rank, (i, _) in enumerate(sorted(scores.items(), key=lambda kv: -kv[1])):
            fused[i] += 1.0 / (RRF_K + rank + 1)
    return fused


class Retriever:
    def __init__(self, docs: list[dict], graph: nx.Graph):
        self.graph = graph
        self.chunks: list[dict] = []
        self.doc_index: dict[str, list[int]] = defaultdict(list)
        for doc in docs:
            for i, ch in enumerate(doc["chunks"]):
                self.doc_index[f"doc:{doc['name']}"].append(len(self.chunks))
                self.chunks.append({
                    "doc": doc["name"], "doc_node": f"doc:{doc['name']}",
                    "chunk_id": f"{doc['name']}#{i}",
                    "heading": ch["heading"], "text": ch["text"],
                    "url": doc["url"], "region": doc["region"], "category": doc["category"],
                })
        indexed = [((c["heading"] + " ") * HEADING_WEIGHT + c["text"]) for c in self.chunks]
        self.plain = [strip_accents(t) for t in indexed]
        self.by_region: dict[str, list[int]] = defaultdict(list)
        self.by_category: dict[str, list[int]] = defaultdict(list)
        for i, c in enumerate(self.chunks):
            self.by_region[c["region"]].append(i)
            self.by_category[c["category"]].append(i)
        self.plain_words = [set(word_tokens(p)) for p in self.plain]
        n = max(len(self.plain_words), 1)
        df: dict[str, int] = defaultdict(int)
        for words in self.plain_words:
            for t in words:
                df[t] += 1
        self.cover_idf = {t: math.log(1.0 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
        self.max_idf = math.log(1.0 + (n + 0.5) / 0.5)
        self.word = Bm25([word_tokens(t) for t in indexed])
        self.ngram = Bm25([ngram_tokens(t) for t in indexed], k1=1.2, b=0.6)
        self.admin_labels = {
            strip_accents(d["label"]) for _, d in graph.nodes(data=True)
            if is_admin_name(d.get("label", ""))
        }


    
    def _score_chunks(
        self,
        cand: set[int],
        lexical: dict[int, float],
        seed_labels: list[str],
        intent: frozenset[str],
        q_words: set[str],
    ) -> list[dict]:
        best = max((lexical.get(i, 0.0) for i in cand), default=0.0) or 1.0
        out: list[dict] = []
        for i in cand:
            c = self.chunks[i]
            raw = lexical.get(i, 0.0)
            lex = raw / best
            hits = [lb for lb in seed_labels if contains_name(self.plain[i], lb)]
            intent_bonus = self._intent_bonus(intent, c)
            out.append({
                **c,
                "chunk_score": round(
                    lex + CHUNK_ENTITY_BONUS * min(len(hits), 3) + intent_bonus, 4
                ),
                "lexical": round(lex, 4),
                "lexical_raw": round(raw, 6),   # TUYỆT ĐỐI, cho hiệu chỉnh cổng
                "graph_hits": hits,
                "intent_bonus": round(intent_bonus, 4),
                "coverage": round(self._coverage(q_words, i), 3),
            })
        return out

    def _coverage(self, q_words: set[str], i: int) -> float:
        """Tỉ lệ TRỌNG SỐ IDF của từ khoá câu hỏi có mặt trong chunk."""
        if not q_words:
            return 0.0
        total = sum(self.cover_idf.get(t, self.max_idf) for t in q_words)
        if total <= 0:
            return 0.0
        hit = sum(
            self.cover_idf.get(t, self.max_idf)
            for t in q_words & self.plain_words[i]
        )
        return hit / total

    def _named_docs(self, seeds: list[str]) -> set[str]:
        """Bài mà câu hỏi gọi đúng tên - trực tiếp, hoặc qua entity curated cùng tên."""
        out: set[str] = set()
        for s in seeds:
            kind = self.graph.nodes[s].get("kind")
            if kind == "doc":
                out.add(s)
            elif kind == "entity":
                dn = "doc:" + self.graph.nodes[s]["label"]
                if dn in self.graph:
                    out.add(dn)
        return out

    def foreign_admin(self, query: str) -> list[str]:
        return [
            name for name in extract_names(query)
            if is_admin_name(name) and strip_accents(name) not in self.admin_labels
        ]

    def _intent_bonus(self, intent: frozenset[str], chunk: dict) -> float:
        if not intent:
            return 0.0
        bonus = 0.0
        if "location" in intent:
            heading = strip_accents(chunk["heading"])
            if any(h in heading for h in LOCATION_HEADINGS) or is_lead(chunk):
                bonus += INTENT_HEADING_BONUS
        if "ward" in intent and is_admin_chunk(chunk):
            bonus += INTENT_HEADING_BONUS
        if "time" in intent and YEAR_IN_CHUNK_RE.search(chunk["text"]):
            bonus += INTENT_HEADING_BONUS
        return bonus

    def _scope_pool(self, scope: tuple[str, str]) -> set[int] | None:
     
        region, category = scope
        pools = []
        if region:
            pools.append(set(self.by_region.get(region, ())))
        if category:
            pools.append(set(self.by_category.get(category, ())))
        if not pools:
            return None
        pool = set.intersection(*pools)
        return pool or None

  

    def retrieve(self, query: str, top_k: int = 3) -> dict:
        empty: dict = {"hits": [], "seeds": [], "specific": [], "named": [],
                        "subject": "", "anchored": False, "foreign_admin": [],
                        "intent": frozenset(), "scope": ("", ""),
                        "corrections": [], "docs": [], "margin": 0.0,
                        "query_used": ""}
        if not query.strip():
            return empty

        corrections = [] if find_seeds(self.graph, query) else [
            c for c in suggest_corrections(query, self.graph)
            if c["score"] >= MIN_FUZZY_SCORE
        ]
        q_seed = query
        if corrections:
            q_seed = query.replace(corrections[0]["original"], corrections[0]["suggested"])
        q = q_seed

        intent = query_intent(q)
        scope = query_scope(q)

        rankings = [self.word.search(word_tokens(query)),
            self.ngram.search(ngram_tokens(query))]
        
        if FUZZY_UNION:
            rankings = [self.word.search(word_tokens(query)),
                        self.ngram.search(ngram_tokens(query))]
            if q_seed != query:
                rankings += [self.word.search(word_tokens(q_seed)),
                                self.ngram.search(ngram_tokens(q_seed))]
        else:
            rankings = [self.word.search(word_tokens(q)),
                        self.ngram.search(ngram_tokens(q))]
        lexical = _rrf(*rankings)

        seeds = find_seeds(self.graph, q_seed)      # seeds LUÔN dùng câu đã sửa
        named = self._named_docs(seeds)
        anchored = any(
            self.graph.nodes[s].get("kind") in ANCHOR_KINDS for s in seeds
        ) or any(scope)


        foreign = self.foreign_admin(q)
        if foreign and (not named or not GATE_AFTER):
            return {**empty, "foreign_admin": foreign, "corrections": corrections,
                    "intent": intent, "scope": scope, "query_used": q}
        if not lexical and not named:
            return {**empty, "corrections": corrections, "intent": intent,
                    "scope": scope, "query_used": q}

        seed_labels = [
            self.graph.nodes[s]["label"] for s in seeds
            if self.graph.nodes[s].get("kind") in ("entity", "doc")
        ]
        subject, claim_names = subject_and_claims(q, seed_labels)
        if subject:
            named -= {f"doc:{n}" for n in claim_names}

        pool = None if named else self._scope_pool(scope)
        if pool is not None:
            lexical = {i: s for i, s in lexical.items() if i in pool} or lexical

        cand = {i for i, _ in sorted(lexical.items(), key=lambda kv: -kv[1])[:CANDIDATES]}
        for dn in named:
            ranked = sorted(self.doc_index.get(dn, []), key=lambda i: -lexical.get(i, 0.0))
            cand.update(ranked[:INJECT_PER_DOC])
            if INJECT_LEAD and "general" in intent:
                cand.update(i for i in self.doc_index.get(dn, []) if is_lead(self.chunks[i]))

        q_words = set(word_tokens(strip_accents(q)))
        scored = self._score_chunks(cand, lexical, seed_labels, intent, q_words)

        if TWO_TIER:
            docs = rank_documents(scored, expand_docs(self.graph, seeds), named)
            doc_rank = {d["doc_node"]: r for r, d in enumerate(docs)}
            dmap = {d["doc_node"]: d for d in docs}
            for c in scored:
                c["score"] = dmap[c["doc_node"]]["doc_score"]
                c["graph"] = dmap[c["doc_node"]]["graph"]
                c["named"] = c["doc_node"] in named
            scored.sort(key=lambda c: (doc_rank[c["doc_node"]], -c["chunk_score"]))
            margin = docs[0]["doc_score"] - (docs[1]["doc_score"] if len(docs) > 1 else 0.0)
        else:
            g = expand_docs(self.graph, seeds)
            for c in scored:
                gs = g.get(c["doc_node"], 0.0)
                c["graph"] = round(gs, 4)
                c["named"] = c["doc_node"] in named
                c["score"] = round(c["chunk_score"] + GRAPH_WEIGHT * gs
                                    + (NAMED_DOC_BONUS if c["named"] else 0.0), 4)
            scored.sort(key=lambda c: -c["score"])
            top_doc = scored[0]["doc_node"]
            scored.sort(key=lambda c: (c["doc_node"] != top_doc, -c["chunk_score"]))
            docs, margin = [], 0.0

        hits = scored[:top_k]
        if INJECT_LEAD and "general" in intent and hits and not any(is_lead(h) for h in hits):
            lead = next(
                (
                    chunk for chunk in scored
                    if chunk["doc_node"] == hits[0]["doc_node"] and is_lead(chunk)
                ),
                None,
            )
            if lead is not None:
                hits[-1] = lead

        return {
            "hits": hits,
            "docs": docs[:5],
            "margin": round(margin, 4),
            "seeds": [self.graph.nodes[s]["label"] for s in seeds],
            "specific": seed_labels,
            "named": sorted(self.graph.nodes[n]["label"] for n in named),
            "subject": subject,
            "anchored": anchored,
            "foreign_admin": [],
            "intent": intent,
            "scope": scope,
            "corrections": corrections,
            "query_used": q,
        }



    def search(self, query: str, top_k: int = 3) -> list[dict]:
        return self.retrieve(query, top_k)["hits"]


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    """Dựng index + graph 1 lần. Corpus nhỏ nên build trong RAM nhanh hơn là
    đọc lại artifact từ đĩa, và không bao giờ lệch với corpus hiện tại."""
    docs, _skipped = load_docs()
    return Retriever(docs, build_graph(docs))
