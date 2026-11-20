import importlib.util
import io
from pathlib import Path
import re
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from pydantic import ValidationError

from apps.backend.schemas.catalog import ContentCreate


class CatalogMigrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).parents[1] / "migrations/versions/20261120_09_heritage_classification.py"
        spec = importlib.util.spec_from_file_location("catalog_offline_upgrade", path)
        cls.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.migration)

    def test_offline_upgrade_preserves_trigger_bodies_and_never_rewrites_source_records(self):
        output = io.StringIO()
        context = MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output})
        with Operations.context(context):
            self.migration.upgrade()
        sql = output.getvalue()
        self.assertIn("CREATE TRIGGER heritage_catalog_source_trigger", sql)
        self.assertIn("NEW.input_revision := OLD.input_revision+1", sql)
        self.assertIn("CREATE TRIGGER catalog_linked_evidence_trigger", sql)
        self.assertIsNone(re.search(r"^\s*(UPDATE|DELETE FROM)\s+heritage\b", sql, re.MULTILINE | re.IGNORECASE))
        self.assertEqual(self.migration.down_revision, "20261119_highlight_passage")

    def test_schema_removal_is_blocked_until_reviewed_data_has_been_exported(self):
        with self.assertRaisesRegex(RuntimeError, "Export reviewed catalog"):
            self.migration.downgrade()

    def test_new_nonplace_content_requires_real_source_shape_and_fact_citations(self):
        for fields in ({"source_url": "javascript:alert(1)"}, {"source_url": "https://bad host/source"},
                       {"verified_metadata": {"period": {"value": "unknown"}}},
                       {"entity_type_hint": "place"}, {"interactive_highlight_id": True}):
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                ContentCreate.model_validate({"title": "Test", "slug": "test", "entity_type_hint": "artifact",
                    "source_url": "https://example.org/source", **fields})
