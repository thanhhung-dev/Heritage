"""OpenSearch snapshot export, official index/query in an isolated GraphRAG env."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import tempfile
import uuid
from contextlib import redirect_stdout
from importlib.metadata import version
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
VERSION = '3.3.0'
TABLES = ('entities', 'relationships', 'communities', 'community_reports', 'text_units', 'documents')


def export_snapshot(rows, root: Path) -> None:
    """Publish immutable OpenSearch text and its original source mapping."""
    root = root.resolve()
    if root.exists():
        raise FileExistsError('Use a new snapshot directory.')
    if not rows:
        raise ValueError('No passages selected.')
    root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.export-', dir=root.parent) as temporary:
        stage = Path(temporary) / 'snapshot'
        (stage / 'input').mkdir(parents=True)
        manifest = {'snapshot_id': uuid.uuid4().hex, 'graphrag_version': VERSION, 'documents': {}}
        for row in rows:
            identity = str(row['id'])
            filename_id = identity if re.fullmatch(r'[A-Za-z0-9_-]+', identity) else hashlib.sha256(identity.encode()).hexdigest()
            name = f"passage-{filename_id}.txt"
            content = row['text']
            (stage / 'input' / name).write_text(content, encoding='utf-8')
            manifest['documents'][name] = {
                'passage_id': row['id'], 'object_key': row.get('object_key', ''),
                'content_hash': row['content_hash'], 'bucket': row.get('bucket', ''),
                'doc': row.get('location_note') or f"Passage {row['id']}",
                'text_sha256': hashlib.sha256(content.encode()).hexdigest(),
            }
        (stage / 'source-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                                   encoding='utf-8')
        (stage / 'settings.yaml').write_text((PROJECT / 'graphrag/settings.example.yaml').read_text(),
                                             encoding='utf-8')
        stage.rename(root)


def build_global_response(answer, context_reports, reports, communities, units, documents, manifest,
                          *, entities=(), relationships=()):
    """Map considered report communities to R2; this is NOT claim verification."""
    sources = {}
    selected_reports = []
    selected_units = set()
    entity_ids = set()
    relationship_ids = set()
    by_unit = {str(u['id']): u for u in units}
    by_document = {str(d['id']): d for d in documents}
    try:
        for report_id in sorted({str(r['id']) for r in context_reports}):
            # Upstream indexer_adapters maps short_id to community, not human_readable_id.
            matches = [r for r in reports if str(r['community']) == report_id]
            if len(matches) != 1:
                raise ValueError('Unknown or ambiguous report community.')
            report = matches[0]
            members = [c for c in communities if str(c['community']) == report_id
                       and c['level'] == report['level']]
            if len(members) != 1 or not len(members[0]['text_unit_ids']):
                raise ValueError('Community has no resolvable text units.')
            selected_units.update(str(i) for i in members[0]['text_unit_ids'])
            entity_ids.update(str(i) for i in members[0].get('entity_ids', ()))
            relationship_ids.update(str(i) for i in members[0].get('relationship_ids', ()))
            selected_reports.append({'report_id': report_id, 'title': report['title'],
                                     'level': int(report['level'])})
            for unit_id in members[0]['text_unit_ids']:
                document = by_document[str(by_unit[str(unit_id)]['document_id'])]
                source = manifest['documents'][document['title']]
                item = sources.setdefault(source['passage_id'], {
                    key: source[key] for key in ('passage_id', 'object_key', 'content_hash', 'bucket', 'doc')
                })
                item.setdefault('report_ids', set()).add(report_id)
    except (KeyError, TypeError) as error:
        raise ValueError('Broken GraphRAG source lineage.') from error
    for item in sources.values():
        item['report_ids'] = sorted(item['report_ids'])
    graph_context = []
    for kind, records, selected_ids, fields in (
        ('relationship', relationships, relationship_ids, ('source', 'target')),
        ('entity', entities, entity_ids, ('title',)),
    ):
        for record in records:
            if str(record['id']) not in selected_ids:
                continue
            unit_ids = {str(i) for i in record['text_unit_ids']}
            # An aggregated description can depend on more than one source.
            # Never relabel a partial set of its lineage as full support.
            if not unit_ids or not unit_ids <= selected_units:
                continue
            passage_ids = sorted({manifest['documents'][
                by_document[str(by_unit[i]['document_id'])]['title']
            ]['passage_id'] for i in unit_ids})
            graph_context.append({
                'kind': kind, 'id': str(record['id']),
                **{key: record[key] for key in fields},
                'source_passage_ids': passage_ids,
            })
    return {'answer': answer, 'snapshot_id': manifest['snapshot_id'],
            'context_reports': selected_reports, 'sources': [sources[k] for k in sorted(sources)],
            'graph_context': graph_context,
            'source_scope': 'community_context', 'grounding_verified': False}


def snapshot_files(root):
    return [root / 'source-manifest.json', root / 'settings.yaml'] + [
        root / 'output' / f'{table}.parquet' for table in TABLES
    ]


def snapshot_hashes(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in snapshot_files(root)}


def load_tables(root):
    import pandas as pd

    tables = {name: pd.read_parquet(root / 'output' / f'{name}.parquet') for name in TABLES}
    if any(table.empty for name, table in tables.items() if name != 'relationships'):
        raise ValueError('Index is empty; inspect extraction/model quality before enabling it.')
    return tables


def configure_worker(root):
    if version('graphrag') != VERSION:
        raise ValueError(f'This adapter requires graphrag=={VERSION}.')
    os.environ.setdefault('GRAPHRAG_MODEL', 'local-model')
    os.environ.setdefault('GRAPHRAG_API_BASE', os.environ.get('LLAMA_SERVER_URL',
                                                          'http://127.0.0.1:8080').rstrip('/') + '/v1')
    os.environ.setdefault('GRAPHRAG_LLM_API_KEY', 'local-not-a-secret')
    # This is a dedicated CLI/subprocess, never the backend process.
    os.chdir(root)
    from graphrag.config.load_config import load_config

    return load_config(root)


async def index_snapshot(root):
    config = configure_worker(root)
    if (root / 'index-ready.json').exists():
        raise FileExistsError('Never reindex a published snapshot; export a new one.')
    manifest = json.loads((root / 'source-manifest.json').read_text())
    for name, source in manifest['documents'].items():
        if hashlib.sha256((root / 'input' / name).read_bytes()).hexdigest() != source['text_sha256']:
            raise ValueError('Exported text changed since R2 verification.')
    from graphrag.api import build_index

    results = await build_index(config=config)
    if not results or any(result.error for result in results):
        raise RuntimeError('GraphRAG indexing failed; snapshot not published.')
    tables = load_tables(root)
    # Check every report's R2 lineage before the snapshot becomes queryable.
    build_global_response('', [{'id': str(c)} for c in tables['community_reports']['community']],
                          *[tables[t].to_dict('records') for t in
                            ('community_reports', 'communities', 'text_units', 'documents')], manifest,
                          entities=tables['entities'].to_dict('records'),
                          relationships=tables['relationships'].to_dict('records'))
    (root / 'index-ready.json').write_text(json.dumps(snapshot_hashes(root)), encoding='utf-8')
    return {'snapshot_id': manifest['snapshot_id'],
            'tables': {name: len(table) for name, table in tables.items()}}


async def query_snapshot(root, message, community_level):
    if json.loads((root / 'index-ready.json').read_text()) != snapshot_hashes(root):
        raise ValueError('Published snapshot changed; create and index a new snapshot.')
    config = configure_worker(root)
    tables = load_tables(root)
    if community_level not in set(tables['community_reports']['level']):
        raise ValueError('Requested community level is absent from this snapshot.')
    from graphrag.api import global_search

    answer, context = await global_search(
        config=config, entities=tables['entities'], communities=tables['communities'],
        community_reports=tables['community_reports'], community_level=community_level,
        dynamic_community_selection=False,
        response_type='Multiple paragraphs in Vietnamese. Preserve [Data: Reports (...)] citations.',
        query=message,
    )
    if not isinstance(answer, str) or not answer.strip() or not isinstance(context, dict):
        raise ValueError('Unsupported GraphRAG response.')
    context_reports = context['reports'].to_dict('records') if 'reports' in context else []
    manifest = json.loads((root / 'source-manifest.json').read_text())
    return build_global_response(answer, context_reports,
                                 *[tables[t].to_dict('records') for t in
                                   ('community_reports', 'communities', 'text_units', 'documents')], manifest,
                                 entities=tables['entities'].to_dict('records'),
                                 relationships=tables['relationships'].to_dict('records'))


async def export_from_search(root, limit, passage_ids):
    from apps.backend.core.search import PassageStore

    async with PassageStore() as store:
        rows = await store.export_passages(limit, passage_ids)
    export_snapshot(rows, root)
    return {'root': str(root), 'passage_count': len(rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('export', 'index', 'query'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--passage-ids', nargs='*', default=[])
    args = parser.parse_args()
    if args.limit <= 0:
        parser.error('--limit must be positive')
    root = args.root.resolve()
    try:
        if args.env_file:
            from dotenv import load_dotenv
            load_dotenv(args.env_file, override=False)
        # Upstream progress output must not corrupt the worker's JSON protocol.
        with redirect_stdout(sys.stderr):
            if args.command == 'export':
                result = asyncio.run(export_from_search(root, args.limit, args.passage_ids))
            elif args.command == 'index':
                result = asyncio.run(index_snapshot(root))
            else:
                request = json.load(sys.stdin)
                result = asyncio.run(query_snapshot(root, request['message'], request.get('community_level', 0)))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as error:
        # No raw exceptions: DB URLs, signed URLs or API keys may be embedded.
        print(f'GraphRAG {args.command} failed ({type(error).__name__}).', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
