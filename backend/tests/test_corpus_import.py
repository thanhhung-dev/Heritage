import unittest

from backend.db.import_corpus import build_import_plan


class CorpusImportPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = build_import_plan()

    def test_plan_contains_all_usable_corpus_documents_and_passages(self) -> None:
        self.assertEqual(len(self.plan.documents), 45)
        self.assertEqual(len(self.plan.passages), 349)
        self.assertEqual(len(self.plan.entities), 45)

    def test_plan_is_deterministic(self) -> None:
        second = build_import_plan()

        self.assertEqual(self.plan.documents, second.documents)
        self.assertEqual(self.plan.passages, second.passages)
        self.assertEqual(self.plan.entities, second.entities)
        self.assertEqual(self.plan.aliases, second.aliases)
        self.assertEqual(self.plan.locations, second.locations)

    def test_categories_map_to_supported_entity_types(self) -> None:
        entity_types = {entity["type"] for entity in self.plan.entities}

        self.assertEqual(entity_types, {"place", "event", "artifact"})

    def test_verified_location_uses_official_source(self) -> None:
        self.assertEqual(len(self.plan.locations), 1)
        location = self.plan.locations[0]

        self.assertEqual(location["entity_normalized_name"], "cung an dinh")
        self.assertEqual(location["address"], "97 đường Phan Đình Phùng")
        self.assertEqual(location["verification_status"], "verified")
        self.assertIn("hueworldheritage.org.vn", location["source_url"])
        self.assertIn("97 đường Phan Đình Phùng", location["source_sentence"])

    def test_curated_typo_alias_is_imported_with_lower_confidence(self) -> None:
        alias = next(
            alias for alias in self.plan.aliases if alias["alias"] == "Lăng An Định"
        )

        self.assertEqual(alias["entity_normalized_name"], "cung an dinh")
        self.assertEqual(alias["alias_type"], "typo")
        self.assertLess(alias["confidence"], 1.0)


if __name__ == "__main__":
    unittest.main()
