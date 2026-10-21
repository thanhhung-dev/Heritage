"""OpenSearch owns passage text, BM25, vector indexing and hybrid scoring."""
from __future__ import annotations

import json
import math
import os
import re
from urllib.parse import urlsplit

import httpx

from apps.backend.core.embedding import EMBEDDING_DIMENSION, EMBEDDING_ID


class SearchError(RuntimeError):
    """Safe-to-display dependency failure, without URLs or server bodies."""


class PassageStore:
    def __init__(self, *, url=None, index=None, client=None):
        self.url = (url or os.environ.get('OPENSEARCH_URL', 'http://127.0.0.1:9200')).rstrip('/')
        self.index = index or os.environ.get('OPENSEARCH_INDEX', 'heritage-passages-v1')
        parsed = urlsplit(self.url)
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.query or parsed.fragment:
            raise ValueError('OPENSEARCH_URL phải là HTTP(S) URL.')
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', self.index):
            raise ValueError('OPENSEARCH_INDEX chỉ gồm chữ thường, số, dấu gạch ngang/gạch dưới.')
        self.client = client
        self.owned = client is None

    async def __aenter__(self):
        if self.owned:
            username = os.environ.get('OPENSEARCH_USERNAME', '')
            auth = (username, os.environ.get('OPENSEARCH_PASSWORD', '')) if username else None
            self.client = httpx.AsyncClient(timeout=30, auth=auth)
        return self

    async def __aexit__(self, *args):
        if self.owned:
            await self.client.aclose()

    async def _request(self, method, path, **kwargs):
        try:
            response = await self.client.request(method, self.url + path, **kwargs)
            response.raise_for_status()
            result = response.json()
        except (httpx.HTTPError, ValueError):
            raise SearchError('OpenSearch không khả dụng hoặc trả dữ liệu không hợp lệ.') from None
        if result.get('timed_out') or result.get('_shards', {}).get('failed', 0):
            raise SearchError('OpenSearch không hoàn tất truy vấn; không dùng kết quả một phần.')
        return result

    async def ensure_index(self):
        """Explicit ingestion setup, never executed on the question-answer path."""
        mapping = {
            'settings': {
                'index.knn': True, 'number_of_shards': 1, 'number_of_replicas': 0,
                'analysis': {
                    'char_filter': {'vietnamese_d': {'type': 'mapping', 'mappings': ['đ => d', 'Đ => D']}},
                    'analyzer': {'vietnamese_folded': {
                        'type': 'custom', 'char_filter': ['vietnamese_d'],
                        'tokenizer': 'standard', 'filter': ['lowercase', 'asciifolding'],
                    }},
                },
            },
            'mappings': {'dynamic': 'strict', 'properties': {
                **{name: {'type': 'keyword'} for name in (
                    'id', 'document_key', 'source_url', 'object_key', 'bucket',
                    'content_hash', 'embedding_model',
                )},
                'text': {'type': 'text', 'analyzer': 'vietnamese_folded'},
                'location_note': {'type': 'text', 'analyzer': 'vietnamese_folded'},
                'passage_index': {'type': 'integer'},
                'embedding': {'type': 'knn_vector', 'dimension': EMBEDDING_DIMENSION,
                              'method': {'name': 'hnsw', 'engine': 'faiss',
                                         'space_type': 'cosinesimil'}},
            }},
        }
        try:
            response = await self.client.put(f'{self.url}/{self.index}', json=mapping)
            exists = (response.status_code == 400 and
                      response.json().get('error', {}).get('type') == 'resource_already_exists_exception')
            if not exists:
                response.raise_for_status()
        except (httpx.HTTPError, ValueError):
            raise SearchError('Không tạo được passage index trong OpenSearch.') from None
        await self._request('PUT', f'/_search/pipeline/{self.index}-hybrid', json={
            'phase_results_processors': [{'normalization-processor': {
                'normalization': {'technique': 'min_max'},
                'combination': {'technique': 'arithmetic_mean', 'parameters': {'weights': [0.5, 0.5]}},
            }}],
        })

    async def index_passages(self, rows):
        for start in range(0, len(rows), 32):
            lines = []
            for row in rows[start:start + 32]:
                lines.extend((json.dumps({'index': {'_index': self.index, '_id': row['id']}}),
                              json.dumps(row, ensure_ascii=False, allow_nan=False)))
            result = await self._request('POST', '/_bulk', params={'refresh': 'wait_for'},
                                         content='\n'.join(lines) + '\n',
                                         headers={'Content-Type': 'application/x-ndjson'})
            if result.get('errors'):
                raise SearchError('Một số passage chưa được index; sửa lỗi và import lại để hoàn tất batch.')

    async def search(self, question, vector, limit=20):
        threshold = float(os.environ.get('PASSAGE_MIN_SIMILARITY', '0.55'))
        if not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError('PASSAGE_MIN_SIMILARITY phải nằm trong [0, 1].')
        model_filter = {'term': {'embedding_model': EMBEDDING_ID}}
        result = await self._request('POST', f'/{self.index}/_search',
            params={'search_pipeline': f'{self.index}-hybrid'}, json={
                'size': limit, '_source': {'excludes': ['embedding']},
                'query': {'hybrid': {'queries': [
                    {'bool': {'filter': [model_filter], 'must': [{'multi_match': {
                        'query': question, 'fields': ['text', 'location_note^2'],
                        'minimum_should_match': '50%',
                    }}]}},
                    {'function_score': {
                        'query': {'knn': {'embedding': {
                            'vector': vector, 'filter': model_filter, 'k': limit,
                        }}},
                        # Faiss cosine score = (1 + cosine) / 2. Gate returned
                        # scores: 3.3's filtered exact radial fallback converts
                        # knn.min_score incorrectly for cosinesimil.
                        'min_score': (1 + threshold) / 2,
                    }},
                ]}},
            })
        return [{**hit['_source'], 'id': hit['_id'], 'score': hit['_score']}
                for hit in result['hits']['hits']]

    async def get_passages(self, ids):
        if not ids:
            return []
        result = await self._request('POST', f'/{self.index}/_mget', json={
            'ids': list(dict.fromkeys(str(i) for i in ids)),
        }, params={'_source_excludes': 'embedding'})
        if any('error' in hit for hit in result['docs']):
            raise SearchError('Không đọc được passage từ OpenSearch.')
        return [{**hit['_source'], 'id': hit['_id']} for hit in result['docs']
                if hit.get('found') and hit['_source']['embedding_model'] == EMBEDDING_ID]

    async def export_passages(self, limit, ids=()):
        """Read bounded pages for offline GraphRAG exports, not runtime inventory scans."""
        rows = []
        after = None
        filters = [{'term': {'embedding_model': EMBEDDING_ID}}]
        if ids:
            filters.append({'ids': {'values': [str(i) for i in ids]}})
        while len(rows) < limit:
            body = {'size': min(100, limit - len(rows)), 'sort': ['id'],
                    '_source': {'excludes': ['embedding']}, 'query': {'bool': {'filter': filters}}}
            if after:
                body['search_after'] = after
            result = await self._request('POST', f'/{self.index}/_search', json=body)
            hits = result['hits']['hits']
            if not hits:
                break
            rows.extend({**h['_source'], 'id': h['_id']} for h in hits)
            after = hits[-1]['sort']
        return rows
