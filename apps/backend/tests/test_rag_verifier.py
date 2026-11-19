"""Disposable-database runner must reject unsafe or incomplete setup before connecting."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]


class RagVerifierGuardsTests(unittest.TestCase):
    def run_verifier(self, url, *args):
        environment = {**os.environ, 'DATABASE_URL': url, 'OPENSEARCH_TEST_URL': '', 'RAG_TEST_R2_OBJECT_KEY': ''}
        return subprocess.run([sys.executable, '-X', 'utf8', 'scripts/sprint4/verify_rag_postgres.py', *args],
            cwd=ROOT, env=environment, capture_output=True, text=True, timeout=10)

    def test_remote_application_database_is_refused_without_connection(self):
        result = self.run_verifier('postgresql+psycopg://user:private-password@example.invalid/application')
        self.assertEqual(result.returncode, 2)
        self.assertIn('loopback', result.stderr)
        self.assertNotIn('private-password', result.stderr)

    def test_missing_database_url_is_a_sanitized_configuration_error(self):
        result = self.run_verifier('')
        self.assertEqual(result.returncode, 2)
        self.assertIn('valid local PostgreSQL', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_live_mode_requires_explicit_test_resources_before_creating_a_database(self):
        result = self.run_verifier('postgresql+psycopg://user:unused@127.0.0.1:1/application', '--live')
        self.assertEqual(result.returncode, 2)
        self.assertIn('OPENSEARCH_TEST_URL', result.stderr)
        self.assertNotIn('could not connect', result.stderr.lower())

    def test_local_runtime_requires_explicit_local_search_service(self):
        result = self.run_verifier('postgresql+psycopg://user:unused@127.0.0.1:1/application', '--local-runtime')
        self.assertEqual(result.returncode, 2)
        self.assertIn('OPENSEARCH_TEST_URL', result.stderr)
        self.assertNotIn('could not connect', result.stderr.lower())

    def test_local_runtime_does_not_inherit_the_disabled_cloud_gate(self):
        environment = {**os.environ, 'RAG_LIVE_TEST': '0', 'RAG_LOCAL_RUNTIME_TEST': '1'}
        script = ('from apps.backend.tests.test_rag_local_runtime import RagLocalRuntimeTests; '
                  'from apps.backend.tests.test_rag_live import RagLiveTests; '
                  'assert RagLocalRuntimeTests.__unittest_skip__ is False; '
                  'assert RagLiveTests.__unittest_skip__ is True')
        result = subprocess.run([sys.executable, '-X', 'utf8', '-c', script], cwd=ROOT,
                                env=environment, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
