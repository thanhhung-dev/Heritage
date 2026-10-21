"""Run a frozen question set sequentially against the real combined chat API.

R2_BUCKET=knowledge .venv/bin/python -m pipelines.graph.microsoft_graphrag export \
    --root .amp/in/thien-mu-eval-inventory --env-file .env --limit 1000
.venv/bin/python -m pipelines.evaluation.eval_graphrag_chat \
    --limit 50 --output .amp/in/artifacts/thien-mu-50.jsonl

No POST retries, model changes, indexing, or automatic factual grading. A selected
Microsoft source proves source participation, not improvement or answer accuracy.
Use correlation IDs to inspect logs (or optional Langfuse when re-enabled).
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time
import uuid

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--cases', type=Path, default=Path(__file__).with_name('graphrag_chat_cases.json'))
    parser.add_argument('--inventory-root', type=Path, default=Path('.amp/in/thien-mu-eval-inventory'))
    parser.add_argument('--snapshot-root', type=Path, default=Path('graphrag/runs/thien-mu-mvp'))
    parser.add_argument('--limit', type=int, default=50, help='Maximum cases per run (default: 50).')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.limit <= 0:
        parser.error('Limit must be positive.')
    fixture = json.loads(args.cases.read_text())
    cases = fixture['cases'][:args.limit]
    if not cases or len({case['id'] for case in cases}) != len(cases):
        parser.error('Case IDs must be unique and the fixture must not be empty.')
    inventory = json.loads((args.inventory_root / 'source-manifest.json').read_text())
    inventory_ids = {str(source['passage_id']) for source in inventory['documents'].values()}
    for case in cases:
        if any(not group or not {str(i) for i in group} <= inventory_ids for group in case['evidence_groups']):
            parser.error(f'Invalid source group in {case["id"]}.')
    snapshot = json.loads((args.snapshot_root / 'source-manifest.json').read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if any(path.exists() for path in [args.output, args.output.with_suffix('.run.json'),
                                      args.output.with_suffix('.summary.json')]):
        parser.error('Use a new output path; existing runs are never overwritten or retried.')
    paths = [args.cases, args.inventory_root / 'source-manifest.json',
             args.snapshot_root / 'source-manifest.json', args.snapshot_root / 'index-ready.json',
             Path('apps/backend/api/chat.py'), Path('apps/backend/services/passages.py'),
             Path('apps/backend/services/graphrag.py'), Path('apps/backend/core/prompt.py'),
             Path('apps/backend/core/search.py'), Path('apps/backend/core/llm.py')]
    run = {
        'id': f'tm{len(cases)}-' + uuid.uuid4().hex[:12],
        'started_at': datetime.now(timezone.utc).isoformat(),
        'url': args.url, 'case_count': len(cases), 'execution': 'sequential, no retries',
        'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'file_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        'snapshot_id': snapshot['snapshot_id'],
        'snapshot_passage_ids': sorted(source['passage_id'] for source in snapshot['documents'].values()),
        'inventory_count': len(inventory_ids), 'manual_verdict': None,
        'grading': 'HTTP/schema/source diagnostics only; rubric review required for correctness.',
    }
    args.output.with_suffix('.run.json').write_text(json.dumps(run, ensure_ascii=False, indent=2))
    results = []
    with args.output.open('x') as stream, httpx.Client(timeout=600) as client:
        for case in cases:
            correlation = str(uuid.uuid5(uuid.NAMESPACE_URL, run['id'] + '-' + case['id']))
            result = dict(case, correlation_id=correlation,
                          started_at=datetime.now(timezone.utc).isoformat(), manual_verdict=None)
            print(f'START {case["id"]} {case["question"]}', flush=True)
            started = time.perf_counter()
            try:
                response = client.post(args.url.rstrip('/') + '/api/chat',
                    headers={'X-Correlation-ID': correlation},
                    json={'message': case['question'], 'use_rag': True, 'session_id': correlation})
                result['http_status'] = response.status_code
                result['returned_correlation_id'] = response.headers.get('X-Correlation-ID')
                try:
                    payload = response.json()
                except ValueError:
                    payload = {'invalid_json_body': response.text}
                result['response'] = payload
                result['http_expected'] = response.status_code == case.get('expected_http_status', 200)
                schema_ok = (isinstance(payload, dict) and isinstance(payload.get('answer'), str)
                             and isinstance(payload.get('sources'), list)
                             and all(isinstance(s, dict) and isinstance(s.get('passage_id'), str)
                                     and isinstance(s.get('retrieval_methods'), list)
                                     and isinstance(s.get('object_key'), str)
                                     for s in payload['sources']))
                result['schema_expected'] = schema_ok if response.status_code == 200 else None
                if schema_ok:
                    sources = payload['sources']
                    selected = {str(source['passage_id']) for source in sources}
                    result['evidence_group_hits'] = [bool(selected & {str(i) for i in group})
                                                     for group in case['evidence_groups']]
                    result['microsoft_source_selected'] = any(
                        'microsoft_graphrag' in source['retrieval_methods'] for source in sources)
                    result['answer_chars'] = len(payload['answer'])
            except httpx.RequestError as error:
                result['request_error'] = type(error).__name__
            result['seconds'] = round(time.perf_counter() - started, 3)
            stream.write(json.dumps(result, ensure_ascii=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
            results.append(result)
            summary = {
                'run_id': run['id'], 'completed': len(results), 'planned': len(cases),
                'http_statuses': dict(Counter(str(r.get('http_status', 'request_error')) for r in results)),
                'unexpected_http': sum(not r.get('http_expected', False) for r in results),
                'invalid_success_schema': sum(r.get('schema_expected') is False for r in results),
                'microsoft_source_selected': sum(r.get('microsoft_source_selected', False) for r in results),
                'median_seconds': round(statistics.median(r['seconds'] for r in results), 3),
                'total_request_seconds': round(sum(r['seconds'] for r in results), 3),
                'semantic_grading': 'not automatically graded; review answers, final context and rubric',
            }
            args.output.with_suffix('.summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
            print(f'DONE {case["id"]} HTTP={result.get("http_status")} {result["seconds"]}s '
                  f'microsoft_source={result.get("microsoft_source_selected")} '
                  f'{len(results)}/{len(cases)}', flush=True)
            if 'request_error' in result:
                raise SystemExit('Stopped after transport error; server outcome may be unknown. No retry sent.')


if __name__ == '__main__':
    main()
