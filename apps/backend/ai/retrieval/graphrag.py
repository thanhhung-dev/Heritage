"""Optional Microsoft GraphRAG worker, isolated from backend ML dependencies."""
from __future__ import annotations

import asyncio
import json
import math
import os
from pathlib import Path

from apps.backend.common.observability import rag_observation
from apps.backend.common.config import PROJECT_ROOT
from apps.backend.services.tour_scope import resolve_area
from pipelines.graph.microsoft_graphrag import validate_area_snapshot

PROJECT = PROJECT_ROOT
_query_lock = asyncio.Lock()


def graphrag_enabled() -> bool:
    return os.environ.get('GRAPHRAG_ENABLED', 'false').lower() in {'true', '1', 'yes', 'on'}


async def run_global_query(message: str, community_level: int = 0, *,
                           active_area_id: str | None = None) -> dict:
    if not graphrag_enabled():
        raise RuntimeError('Microsoft GraphRAG is disabled.')
    if active_area_id:
        area = resolve_area(active_area_id)
        roots = json.loads(os.environ.get("GRAPHRAG_AREA_ROOTS", "{}"))
        configured_root = roots.get(area.id)
    else:
        configured_root = os.environ.get('GRAPHRAG_ROOT', '')
    if not configured_root:
        raise RuntimeError('Select an indexed snapshot first.')
    root = Path(configured_root).resolve()
    if active_area_id:
        validate_area_snapshot(root, area.id)
    # Resolving a venv interpreter symlink would discard its site-packages.
    python = Path(os.environ.get('GRAPHRAG_PYTHON', str(PROJECT / '.venv-graphrag/bin/python'))).absolute()
    timeout = float(os.environ.get('GRAPHRAG_QUERY_TIMEOUT', '180'))
    if not math.isfinite(timeout) or not 0 < timeout <= 3600:
        raise ValueError('Invalid GraphRAG timeout.')
    if not python.is_file() or not (root / 'index-ready.json').is_file():
        raise RuntimeError('GraphRAG environment or snapshot is not ready.')
    if _query_lock.locked():
        raise RuntimeError('GraphRAG is busy; retry later.')
    async with _query_lock:
        with rag_observation('graphrag.global_search', input={'query': message}, metadata={
            'community_level': community_level, 'method': 'global', 'grounding_verified': False,
        }) as observation:
            process = await asyncio.create_subprocess_exec(
                str(python), '-m', 'pipelines.graph.microsoft_graphrag', 'query', '--root', str(root),
                cwd=PROJECT, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                stdout, _ = await asyncio.wait_for(process.communicate(json.dumps({
                    'message': message, 'community_level': community_level,
                    **({'active_area_id': area.id} if active_area_id else {}),
                }).encode()), timeout=timeout)
                if process.returncode:
                    raise RuntimeError('GraphRAG query failed.')
                result = json.loads(stdout)
                if active_area_id and result.get("active_area_id") != area.id:
                    raise ValueError("GraphRAG returned another area.")
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
            observation.update(output=result, metadata={
                'snapshot_id': result['snapshot_id'],
                'report_count': len(result['context_reports']), 'source_count': len(result['sources']),
            })
            return result
