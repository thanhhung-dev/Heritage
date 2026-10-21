"""Retrieve complete evidence chunks from OpenSearch, never from R2 or PostgreSQL."""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field

from apps.backend.ai.providers.embedding import embed_texts
from apps.backend.common.observability import rag_observation
from apps.backend.common.utils.text import strip_accents
from apps.backend.ai.retrieval.graphrag import graphrag_enabled, run_global_query


@dataclass(frozen=True)
class PassageEvidence:
    id: str
    text: str
    location_note: str = ''
    object_key: str = ''
    retrieval_methods: tuple[str, ...] = ('opensearch_hybrid',)
    score: float = 0.0
    source_url: str = ''

    def to_source(self) -> dict:
        return {'passage_id': self.id, 'chunk_id': self.id,
                'doc': self.location_note or f'Passage {self.id}',
                'url': self.source_url, 'object_key': self.object_key,
                'retrieval_methods': list(self.retrieval_methods), 'score': self.score}


@dataclass
class RetrievalQuery:
    search_text: str
    intent: frozenset[str] = frozenset()
    corrections: list[dict] = field(default_factory=list)
    ambiguous: bool = False


@dataclass(frozen=True)
class PassageSearch:
    query: RetrievalQuery
    evidence: list[PassageEvidence]
    graph_context: list[dict] = field(default_factory=list)


class PassageRepository:
    def __init__(self, store, *, embedder=embed_texts):
        self.store = store
        self.embedder = embedder

    async def search_evidence(self, question: str, limit: int = 2) -> PassageSearch:
        question = question.strip()
        intent = frozenset({'relation'} if re.search(r'\b(lien quan|quan he|so sanh|khac nhau)\b',
                                                    strip_accents(question)) else {'general'})
        query = RetrievalQuery(question, intent=intent)
        if not question or limit <= 0:
            return PassageSearch(query, [])
        with rag_observation('retrieval', as_type='retriever', input={'query': question}) as observation:
            with rag_observation('query.embedding', as_type='embedding'):
                vectors = await asyncio.to_thread(self.embedder, [question])
            with rag_observation('retrieval.opensearch'):
                rows = await self.store.search(question, vectors[0])
            graph_context = []
            methods = {row['id']: ('opensearch_hybrid',) for row in rows}
            if graphrag_enabled() and ('relation' in intent or len(rows) < 3):
                with rag_observation('retrieval.microsoft_graphrag') as graph_observation:
                    try:
                        graph = await run_global_query(question)
                        sources = {str(s['passage_id']): s for s in graph['sources']}
                        graph_rows = await self.store.get_passages(list(sources))
                        current = []
                        for row in graph_rows:
                            source = sources[row['id']]
                            if all(row.get(k, '') == source.get(k, '')
                                   for k in ('content_hash', 'object_key', 'bucket')):
                                current.append(row)
                        current_ids = {row['id'] for row in current}
                        for row in current:
                            if row['id'] not in methods:
                                rows.append(row)
                                methods[row['id']] = ('microsoft_graphrag',)
                            else:
                                methods[row['id']] += ('microsoft_graphrag',)
                        for item in graph.get('graph_context', []):
                            ids = [str(i) for i in item['source_passage_ids']]
                            if ids and set(ids) <= current_ids:
                                graph_context.append({**item, 'source_passage_ids': ids})
                    except Exception as error:
                        graph_observation.update(level='WARNING', status_message=type(error).__name__,
                                                 metadata={'status': 'hybrid_fallback'})
            picked = []
            size = 0
            for row in rows:
                content = row['text']
                cost = len(content) + bool(picked)
                if not content.strip() or size + cost > 4800:
                    continue
                picked.append(PassageEvidence(
                    id=row['id'], text=content, location_note=row.get('location_note', ''),
                    object_key=row.get('object_key', ''), source_url=row.get('source_url', ''),
                    score=float(row.get('score', 0)), retrieval_methods=methods[row['id']],
                ))
                size += cost
                if len(picked) >= min(limit, 2):
                    break
            selected = {p.id for p in picked}
            graph_context = [g for g in graph_context if set(g['source_passage_ids']) <= selected]
            observation.update(output=[p.to_source() for p in picked],
                               metadata={'selected_count': len(picked), 'context_chars': size})
            return PassageSearch(query, picked, graph_context)
