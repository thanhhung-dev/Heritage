import unittest

from apps.backend.db.import_structured import PackageValidationError, validate_package


def valid_package() -> dict:
    text = "Cung An Định còn được gọi là An Dinh Palace."
    return {
        "corpus_version": 2,
        "documents": [{
            "key": "doc", "title": "Nguồn chính thức", "region": "hue",
            "source_url": "https://example.org/an-dinh", "source_type": "official",
            "tier": 1, "observed_at": "2026-09-28T00:00:00Z", "raw_text": text,
        }],
        "passages": [{"key": "p1", "document_key": "doc", "text": text,
                       "char_start": 0, "char_end": len(text)}],
        "entities": [{"key": "e1", "name": "Cung An Định", "type": "place",
                      "passage_key": "p1", "quote": "Cung An Định"}],
        "aliases": [{"entity_key": "e1", "alias": "An Dinh Palace",
                     "passage_key": "p1", "quote": "An Dinh Palace",
                     "alias_type": "english"}],
    }


class StructuredImportTests(unittest.TestCase):
    def test_valid_package_preserves_exact_provenance(self) -> None:
        package = valid_package()
        self.assertIs(validate_package(package), package)

    def test_bad_span_is_rejected_before_database_write(self) -> None:
        package = valid_package()
        package["passages"][0]["char_end"] -= 1
        with self.assertRaisesRegex(PackageValidationError, "does not match document span"):
            validate_package(package)

    def test_bad_quote_reference_is_rejected(self) -> None:
        package = valid_package()
        package["entities"][0]["quote"] = "nguồn không tồn tại"
        with self.assertRaisesRegex(PackageValidationError, "quote"):
            validate_package(package)


if __name__ == "__main__":
    unittest.main()
