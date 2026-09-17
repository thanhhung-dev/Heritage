import unittest

from backend.db.migrate import (
    BASELINE_TABLES,
    LEGACY_VIEW,
    classify_unversioned_schema,
)


class MigrationBootstrapTests(unittest.TestCase):
    def test_empty_database_can_run_all_migrations(self) -> None:
        self.assertEqual(classify_unversioned_schema(set(), set()), "empty")

    def test_complete_legacy_schema_can_be_adopted(self) -> None:
        self.assertEqual(
            classify_unversioned_schema(BASELINE_TABLES, {LEGACY_VIEW}),
            "legacy",
        )

    def test_complete_schema_without_version_can_be_adopted(self) -> None:
        self.assertEqual(
            classify_unversioned_schema(
                BASELINE_TABLES | {"place_location"}, {LEGACY_VIEW}
            ),
            "legacy",
        )

    def test_partial_schema_is_rejected_instead_of_blindly_stamped(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported unversioned schema"):
            classify_unversioned_schema({"admin_account"}, set())

    def test_schema_with_unknown_table_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported unversioned schema"):
            classify_unversioned_schema(BASELINE_TABLES | {"custom_data"}, {LEGACY_VIEW})


if __name__ == "__main__":
    unittest.main()
