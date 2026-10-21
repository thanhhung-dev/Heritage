"""Import local passage JSON/package into OpenSearch; never write PostgreSQL/R2."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path

from dotenv import load_dotenv

from apps.backend.core.embedding import EMBEDDING_DIMENSION, EMBEDDING_ID, embed_texts
from apps.backend.core.search import PassageStore


async def import_passages(payload: object, *, store=None, embedder=embed_texts,
                          reuse_embeddings=False) -> int:
    rows = payload.get('passages') if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise ValueError('Cần danh sách passages không rỗng.')
    documents = {d['key']: d for d in payload.get('documents', [])} if isinstance(payload, dict) else {}
    values = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f'passages[{index}] phải là object.')
        content = row.get('text')
        position = row.get('passage_index', index)
        if not isinstance(content, str) or not content.strip() or '\x00' in content:
            raise ValueError(f'passages[{index}].text không hợp lệ.')
        if type(position) is not int or position < 0:
            raise ValueError('passage_index phải là số nguyên >= 0.')
        doc = documents.get(row.get('document_key'), {})
        metadata = {
            'location_note': row.get('location_note') or doc.get('title') or '',
            'source_url': row.get('source_url') or doc.get('source_url') or '',
            'document_key': row.get('document_key') or '',
            'object_key': row.get('source_object_key') or row.get('object_key') or doc.get('object_key') or '',
            'bucket': row.get('bucket') or os.environ.get('R2_BUCKET', ''),
        }
        if any(not isinstance(v, str) for v in metadata.values()):
            raise ValueError('Metadata passage phải là text.')
        digest = hashlib.sha256(content.encode()).hexdigest()
        identity = json.dumps([metadata['document_key'], metadata['source_url'], position, digest], ensure_ascii=False)
        passage_id = str(row.get('id') or row.get('key') or hashlib.sha256(identity.encode()).hexdigest())
        if not passage_id or len(passage_id.encode()) > 512:
            raise ValueError('ID passage phải từ 1 đến 512 byte.')
        value = {**metadata, 'id': passage_id, 'text': content, 'passage_index': position,
                 'content_hash': row.get('content_hash', digest) if reuse_embeddings else digest,
                 'embedding_model': EMBEDDING_ID}
        if reuse_embeddings:
            if row.get('embedding_model') != EMBEDDING_ID:
                raise ValueError('Chỉ tái sử dụng vector cùng phiên bản BGE-M3.')
            value['embedding'] = row.get('embedding')
        if passage_id in values and values[passage_id] != value:
            raise ValueError('ID trùng với nội dung/metadata khác trong cùng batch.')
        values[passage_id] = value
    values = list(values.values())
    if not reuse_embeddings:
        vectors = await asyncio.to_thread(embedder, [
            f"{row['location_note']}\n{row['text']}" if row['location_note'] else row['text']
            for row in values
        ])
        if len(vectors) != len(values):
            raise ValueError('Thiếu embedding; không cập nhật index.')
        for row, vector in zip(values, vectors):
            row['embedding'] = vector
    for row in values:
        vector = row['embedding']
        if (not isinstance(vector, list) or len(vector) != EMBEDDING_DIMENSION
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in vector)
                or not any(vector)):
            raise ValueError('Embedding phải có 1024 số hữu hạn và khác vector zero.')
    if store is None:
        async with PassageStore() as owned:
            await owned.ensure_index()
            await owned.index_passages(values)
    else:
        await store.ensure_index()
        await store.index_passages(values)
    return len(values)


def main() -> int:
    parser = argparse.ArgumentParser(description='passages.json/package.json → BGE-M3 → OpenSearch')
    parser.add_argument('path', type=Path)
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--reuse-embeddings', action='store_true',
                        help='Chỉ dùng cho export tin cậy có vector và embedding_model đúng phiên bản.')
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=False)
    try:
        payload = json.loads(args.path.read_text(encoding='utf-8'))
        count = asyncio.run(import_passages(payload, reuse_embeddings=args.reuse_embeddings))
    except Exception as error:
        # A bulk failure can leave successful items; stable IDs make retries safe.
        print(f'Import OpenSearch thất bại ({type(error).__name__}); kiểm tra cấu hình và import lại.')
        return 1
    print(f'Đã index {count} passage (text + vector + metadata) vào OpenSearch.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
