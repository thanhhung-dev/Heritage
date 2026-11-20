import importlib.util
import io
from pathlib import Path
import re
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient


class KnowledgeLibraryContractTests(unittest.TestCase):
    def test_actual_application_mounts_all_protected_library_operations(self):
        from apps.backend.app import app
        paths = app.openapi()["paths"]
        expected = {"/objects": ("get", "delete"), "/object": ("get",), "/upload-url": ("post",),
                    "/uploads/{uploadId}/complete": ("post",), "/folders": ("post",),
                    "/preview": ("get",), "/download-url": ("post",)}
        for suffix, methods in expected.items():
            path = "/api/admin/knowledge" + suffix
            for method in methods:
                self.assertTrue(paths[path][method]["security"])
        # No lifespan startup/model download/database needed to reject no token.
        client = TestClient(app)
        self.addCleanup(client.close)
        self.assertEqual(client.get("/api/admin/knowledge/objects").status_code, 401)

    def test_offline_migration_is_additive_and_has_correct_parent(self):
        path = Path(__file__).parents[1] / "migrations/versions/20261120_10_knowledge_library.py"
        spec = importlib.util.spec_from_file_location("knowledge_offline_migration", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        out = io.StringIO()
        with Operations.context(MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": out})):
            module.upgrade()
        sql = out.getvalue()
        self.assertIn("CREATE TABLE knowledge_library_upload", sql)
        self.assertIsNone(re.search(r"\b(DROP|DELETE|UPDATE|ALTER)\b", sql))
        self.assertEqual(module.down_revision, "20261120_classification")
        with self.assertRaises(RuntimeError):
            module.downgrade()
