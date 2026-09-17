import json
import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class DockerDatabaseConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        env = os.environ | {
            "POSTGRES_DB": "heritagegraph",
            "POSTGRES_USER": "heritagegraph",
            "POSTGRES_PASSWORD": "test-password",
            # A host-side URL in .env must not leak into containers.
            "DATABASE_URL": "postgresql+asyncpg://local:wrong@localhost:5433/local",
        }
        result = subprocess.run(
            ["docker", "compose", "config", "--format", "json"],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        cls.config = json.loads(result.stdout)

    def test_complete_stack_contains_database_migration_and_frontend(self) -> None:
        self.assertTrue(
            {"db", "migrate", "import-data", "backend", "frontend", "llm"}
            <= self.config["services"].keys()
        )

    def test_docker_context_keeps_orm_models(self) -> None:
        patterns = (ROOT / ".dockerignore").read_text().splitlines()

        self.assertIn("models", patterns)
        self.assertIn("!backend/models", patterns)
        self.assertIn("!backend/models/*.py", patterns)
        self.assertGreater(
            patterns.index("backend/models/qwen2.5-7b"),
            patterns.index("!backend/models/*.py"),
        )

    def test_database_is_internal_and_persistent(self) -> None:
        database = self.config["services"]["db"]

        self.assertNotIn("ports", database)
        self.assertEqual(
            database["volumes"][0]["target"], "/var/lib/postgresql/data"
        )
        self.assertIn("postgres_data", self.config["volumes"])

    def test_backend_waits_for_successful_migration(self) -> None:
        backend_dependencies = self.config["services"]["backend"]["depends_on"]
        importer_dependencies = self.config["services"]["import-data"]["depends_on"]
        migrate_dependencies = self.config["services"]["migrate"]["depends_on"]

        self.assertEqual(
            backend_dependencies["import-data"]["condition"],
            "service_completed_successfully",
        )
        self.assertEqual(
            importer_dependencies["migrate"]["condition"],
            "service_completed_successfully",
        )
        self.assertEqual(migrate_dependencies["db"]["condition"], "service_healthy")

    def test_migration_service_adopts_supported_legacy_schema(self) -> None:
        self.assertEqual(
            self.config["services"]["migrate"]["command"],
            ["python", "-m", "backend.db.migrate"],
        )

    def test_database_url_uses_compose_service_and_internal_port(self) -> None:
        expected = (
            "postgresql+psycopg://heritagegraph:test-password@db:5432/heritagegraph"
        )

        self.assertEqual(
            self.config["services"]["backend"]["environment"]["DATABASE_URL"],
            expected,
        )
        self.assertEqual(
            self.config["services"]["migrate"]["environment"]["DATABASE_URL"],
            expected,
        )
        self.assertEqual(
            self.config["services"]["import-data"]["environment"]["DATABASE_URL"],
            expected,
        )


if __name__ == "__main__":
    unittest.main()
