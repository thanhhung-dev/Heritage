"""Retrieve complete evidence chunks from OpenSearch, never from R2 or PostgreSQL."""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field

from apps.backend.core.embedding import embed_texts
from apps.backend.core.observability import rag_observation
from apps.backend.core.textutil import strip_accents
from apps.backend.services.graphrag import graphrag_enabled, run_global_query


from apps.backend.services.tour_scope import mentions_foreign_site, question_outside_area, resolve_area


class EmbeddingError(RuntimeError):
    """Query embedding failed before passage search could run."""


@dataclass(frozen=True)
class PassageEvidence:
    id: str
    text: str
    location_note: str = ''
    object_key: str = ''
    retrieval_methods: tuple[str, ...] = ('opensearch_hybrid',)
    score: float = 0.0
    source_url: str = ''
    active_area_id: str | None = None

    def to_source(self) -> dict:
        return {'passage_id': self.id, 'chunk_id': self.id,
                'doc': self.location_note or f'Passage {self.id}',
                'url': self.source_url, 'object_key': self.object_key,
                'retrieval_methods': list(self.retrieval_methods), 'score': self.score,
                **({'active_area_id': self.active_area_id} if self.active_area_id else {})}


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

    async def search_evidence(self, question: str, limit: int = 2, *, active_area_id: str | None = None) -> PassageSearch:
        question = question.strip()
        intent = frozenset({'relation'} if re.search(r'\b(lien quan|quan he|so sanh|khac nhau)\b',
                                                    strip_accents(question)) else {'general'})
        query = RetrievalQuery(question, intent=intent)
        area = resolve_area(active_area_id) if active_area_id is not None else None
        if not question or limit <= 0 or (area and question_outside_area(question, area)):
            return PassageSearch(query, [])
        retrieval_text = f'{area.title}: {question}' if area else question

        def in_scope(row):
            return area is None or (row.get('active_area_id') == area.id
                and not mentions_foreign_site(row.get('text', '') + ' ' + row.get('location_note', ''), area))

        with rag_observation('retrieval', as_type='retriever', input={'query': question}) as observation:
            with rag_observation('query.embedding', as_type='embedding'):
                try:
                    vectors = await asyncio.to_thread(self.embedder, [retrieval_text])
                except Exception as error:
                    raise EmbeddingError('Không thể tạo embedding cho câu hỏi.') from error
            with rag_observation('retrieval.opensearch'):
                options = {'active_area_id': area.id} if area else {}
                rows = [row for row in await self.store.search(retrieval_text, vectors[0], **options) if in_scope(row)]
            graph_context = []
            methods = {row['id']: ('opensearch_hybrid',) for row in rows}
            if graphrag_enabled() and ('relation' in intent or len(rows) < 3):
                with rag_observation('retrieval.microsoft_graphrag') as graph_observation:
                    try:
                        graph = await run_global_query(retrieval_text, **options)
                        if area and graph.get('active_area_id') != area.id:
                            raise ValueError('Graph snapshot is outside the active area')
                        sources = {str(s['passage_id']): s for s in graph['sources']}
                        graph_rows = await self.store.get_passages(list(sources), **options)
                        current = []
                        for row in graph_rows:
                            source = sources[row['id']]
                            if in_scope(row) and all(row.get(k, '') == source.get(k, '')
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
                            if ids and set(ids) <= current_ids and (not area or not mentions_foreign_site(str(item), area)):
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
                    active_area_id=row.get('active_area_id'),
                ))
                size += cost
                if len(picked) >= min(limit, 2):
                    break
            selected = {p.id for p in picked}
            graph_context = [g for g in graph_context if set(g['source_passage_ids']) <= selected]
            observation.update(output=[p.to_source() for p in picked],
                               metadata={'selected_count': len(picked), 'context_chars': size})
            return PassageSearch(query, picked, graph_context)
