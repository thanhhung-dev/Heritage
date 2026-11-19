"""Reject unsafe manual-test setup before creating databases or cloud objects."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]


class ManualLauncherGuardsTests(unittest.TestCase):
    def launch(self, url, *args):
        return subprocess.run([sys.executable, "-X", "utf8", "scripts/sprint4/manual_backend.py", *args],
            cwd=ROOT, env={**os.environ, "DATABASE_URL": url, "OPENSEARCH_TEST_URL": ""},
            text=True, capture_output=True, timeout=15)

    def test_remote_database_is_rejected_without_revealing_password(self):
        result = self.launch("postgresql+psycopg://user:private-password@example.invalid/application", "--check")
        self.assertEqual(result.returncode, 2)
        self.assertIn("loopback", result.stderr)
        self.assertNotIn("private-password", result.stdout + result.stderr)
        self.assertNotIn("database removed", result.stdout)

    def test_missing_search_is_rejected_before_connecting_to_postgres(self):
        result = self.launch("postgresql+psycopg://user:unused@127.0.0.1:1/application", "--rag", "--check")
        self.assertEqual(result.returncode, 2)
        self.assertIn("OPENSEARCH_TEST_URL", result.stderr)
        self.assertNotIn("database removed", result.stdout)

    def test_invalid_port_and_missing_url_are_sanitized(self):
        for args in (("--port", "0"), ("--check",)):
            with self.subTest(args=args):
                result = self.launch("", *args)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("database removed", result.stdout)
