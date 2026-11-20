"""Retrieve complete evidence chunks from OpenSearch, never from R2 or PostgreSQL."""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field

from apps.backend.core.embedding import embed_texts
from apps.backend.core.observability import rag_observation
from apps.backend.core.textutil import strip_accents
from apps.backend.services.graphrag import graphrag_enabled, run_global_query
from apps.backend.services.tour_scope import resolve_area
from apps.backend.services.tour_passages import matches_reviewed_passage


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

    async def search_evidence(
        self, question: str, limit: int = 6, *, active_area_id: str | None = None,
        artifact_key: str | None = None, passage_links: dict[str, dict[str, str]] | None = None,
    ) -> PassageSearch:
        question = question.strip()
        intent = frozenset({'relation'} if re.search(r'\b(lien quan|quan he|so sanh|khac nhau)\b',
                                                    strip_accents(question)) else {'general'})
        query = RetrievalQuery(question, intent=intent)
        area = resolve_area(active_area_id) if active_area_id is not None else None
        if not question or limit <= 0 or passage_links is not None and not passage_links:
            return PassageSearch(query, [])
        retrieval_text = f'{area.title}: {question}' if area else question

        def in_scope(row):
            return (
                (area is None or row.get('active_area_id') == area.id)
                and (artifact_key is None or artifact_key in row.get('artifact_keys', []))
                and (passage_links is None or row.get('id') in passage_links
                     and matches_reviewed_passage(row, passage_links[row['id']]))
            )

        with rag_observation('retrieval', as_type='retriever', input={'query': question}) as observation:
            with rag_observation('query.embedding', as_type='embedding'):
                try:
                    vectors = await asyncio.to_thread(self.embedder, [retrieval_text])
                except Exception as error:
                    raise EmbeddingError('Không thể tạo embedding cho câu hỏi.') from error
            with rag_observation('retrieval.opensearch'):
                options = {}
                if area:
                    options['active_area_id'] = area.id
                if artifact_key:
                    options['artifact_key'] = artifact_key
                if passage_links is not None:
                    options['passage_ids'] = list(passage_links)
                rows = [row for row in await self.store.search(retrieval_text, vectors[0], **options)
                        if in_scope(row)]
            graph_context = []
            methods = {row['id']: ('opensearch_hybrid',) for row in rows}
            if graphrag_enabled():
                with rag_observation('retrieval.microsoft_graphrag') as graph_observation:
                    try:
                        graph_options = {'active_area_id': area.id} if area else {}
                        graph = await run_global_query(retrieval_text, **graph_options)
                        if area and graph.get('active_area_id') != area.id:
                            raise ValueError('Graph snapshot is outside the active area')
                        sources = {str(s['passage_id']): s for s in graph['sources']
                                   if passage_links is None or str(s['passage_id']) in passage_links}
                        graph_rows = await self.store.get_passages(
                            list(sources), **{key: value for key, value in options.items() if key != 'passage_ids'},
                        )
                        current = []
                        for row in graph_rows:
                            source = sources.get(row['id'])
                            if source and in_scope(row) and all(row.get(k, '') == source.get(k, '')
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
                    active_area_id=row.get('active_area_id'),
                ))
                size += cost
                if len(picked) >= limit:
                    break
            selected = {p.id for p in picked}
            graph_context = [g for g in graph_context if set(g['source_passage_ids']) <= selected]
            observation.update(output=[p.to_source() for p in picked],
                               metadata={'selected_count': len(picked), 'context_chars': size})
            return PassageSearch(query, picked, graph_context)
