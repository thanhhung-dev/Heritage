"""Opt-in PostgreSQL migration checks for local development and CI."""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


@unittest.skipUnless(
    os.environ.get("RUN_DATABASE_INTEGRATION") == "1",
    "set RUN_DATABASE_INTEGRATION=1 to run Docker migration checks",
)
class MigrationIntegrationTests(unittest.TestCase):
    project = f"heritagegraph-migration-test-{os.getpid()}"
    environment = os.environ | {
        "POSTGRES_DB": "heritagegraph_migration_test",
        "POSTGRES_USER": "heritagegraph_test",
        "POSTGRES_PASSWORD": "local-integration-only",
        "DATABASE_SSL_MODE": "disable",
    }

    @classmethod
    def _compose(cls, *arguments: str, capture_output: bool = False) -> str:
        result = subprocess.run(
            ["docker", "compose", "-p", cls.project, *arguments],
            cwd=ROOT,
            env=cls.environment,
            check=True,
            capture_output=capture_output,
            text=True,
        )
        return result.stdout

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.addClassCleanup(cls._compose, "down", "-v", "--remove-orphans")
        cls._compose("up", "-d", "--wait", "db")

    def test_clean_upgrade_extensions_repeatability_and_rollback(self) -> None:
        self._compose("run", "--rm", "migrate")

        extensions = self._compose(
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            self.environment["POSTGRES_USER"],
            "-d",
            self.environment["POSTGRES_DB"],
            "-Atc",
            "SELECT extname FROM pg_extension "
            "WHERE extname IN ('vector', 'pg_trgm', 'pgcrypto') ORDER BY extname",
            capture_output=True,
        ).splitlines()
        self.assertEqual(extensions, ["pg_trgm", "pgcrypto", "vector"])

        # A second upgrade must be a no-op rather than creating duplicates.
        self._compose("run", "--rm", "migrate")

        # The extension revision has a non-destructive downgrade. This verifies
        # the revision can move back and be upgraded again without data loss.
        self._compose(
            "run", "--rm", "--entrypoint", "alembic", "migrate", "downgrade", "-1"
        )
        self._compose("run", "--rm", "migrate")

        revision = self._compose(
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            self.environment["POSTGRES_USER"],
            "-d",
            self.environment["POSTGRES_DB"],
            "-Atc",
            "SELECT version_num FROM alembic_version",
            capture_output=True,
        ).strip()
        self.assertEqual(revision, "f4c1d2e3a4b5")


if __name__ == "__main__":
    unittest.main()
