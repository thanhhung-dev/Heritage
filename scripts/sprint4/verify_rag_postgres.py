"""Run RAG integration checks in an owned disposable local PostgreSQL database.

Reads existing local connection credentials without printing them. Does not
apply migrations to the application database. --live additionally requires
explicit OpenSearch/R2 test resources and already cached BGE-M3 dependencies.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

from dotenv import dotenv_values
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--live', action='store_true', help='Also run the explicit cloud full-stack smoke test')
    mode.add_argument('--local-runtime', action='store_true',
                      help='Run real local model/search with a protocol fixture instead of cloud R2')
    args = parser.parse_args()
    values = {**dotenv_values(ROOT / '.env'), **os.environ}
    try:
        url = make_url(values.get('DATABASE_URL', ''))
    except (ArgumentError, TypeError, ValueError):
        parser.error('Configure a valid local PostgreSQL DATABASE_URL')
    if url.drivername != 'postgresql+psycopg' or url.host not in {'127.0.0.1', 'localhost', '::1'}:
        parser.error('Only an explicit loopback postgresql+psycopg connection is permitted')
    if args.live and any(not values.get(key) for key in ('OPENSEARCH_TEST_URL', 'RAG_TEST_R2_OBJECT_KEY', 'R2_BUCKET')):
        parser.error('--live requires OPENSEARCH_TEST_URL, RAG_TEST_R2_OBJECT_KEY and R2_BUCKET')
    if args.local_runtime and not values.get('OPENSEARCH_TEST_URL'):
        parser.error('--local-runtime requires OPENSEARCH_TEST_URL')
    database = 'test_sprint4_' + uuid4().hex
    if not re.fullmatch(r'test_sprint4_[0-9a-f]{32}', database):
        raise RuntimeError('Invalid generated test database name')
    admin_url = url.set(drivername='postgresql').render_as_string(hide_password=False)
    tests = ['apps/backend/tests/test_rag_postgres.py', 'apps/backend/tests/test_sprint4_postgres.py',
             'apps/backend/tests/test_sprint4_application_postgres.py']
    environment = {key: str(value) for key, value in values.items() if value is not None}
    environment['SPRINT4_POSTGRES_TEST_URL'] = url.set(database=database).render_as_string(hide_password=False)
    if args.live:
        environment['RAG_LIVE_TEST'] = '1'
        tests.append('apps/backend/tests/test_rag_live.py')
    if args.local_runtime:
        environment['RAG_LOCAL_RUNTIME_TEST'] = '1'
        environment['RAG_LIVE_TEST'] = '0'
        tests.append('apps/backend/tests/test_rag_local_runtime.py')
    created = False
    try:
        with psycopg.connect(admin_url, autocommit=True, connect_timeout=5) as connection:
            version = connection.execute('SHOW server_version').fetchone()[0]
            print('Isolated verification on PostgreSQL', version, flush=True)
            connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
            created = True
        result = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pytest', *tests, '-q'],
                                cwd=ROOT, env=environment)
        return result.returncode
    finally:
        if created:
            with psycopg.connect(admin_url, autocommit=True, connect_timeout=5) as connection:
                connection.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
            print('Disposable database removed; application data unchanged', flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
