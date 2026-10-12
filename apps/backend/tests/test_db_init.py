import unittest

from apps.backend.db.init_db import (
    PREDICATE_SEED,
    REQUIRED_EXTENSIONS,
    SEED_STATEMENTS,
)


class DatabaseInitTests(unittest.TestCase):
    def test_required_extensions_cover_runtime_needs(self) -> None:
        self.assertEqual(
            set(REQUIRED_EXTENSIONS),
            {"pgcrypto", "vector", "pg_trgm", "unaccent"},
        )

    def test_predicate_seed_is_complete_and_unique(self) -> None:
        codes = [row[0] for row in PREDICATE_SEED]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertIn("located_in", codes)

    def test_seed_statements_never_drop_or_delete(self) -> None:
        for statement in SEED_STATEMENTS:
            upper = statement.upper()
            self.assertNotIn("DROP ", upper)
            self.assertNotIn("DELETE ", upper)
            self.assertNotIn("TRUNCATE ", upper)


if __name__ == "__main__":
    unittest.main()
