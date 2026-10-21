import unittest

from pipelines.ingestion.package import (
    PackageValidationError, validate_package,
)


def valid_package() -> dict:
    text = (
        "Cung An Định - Trung tâm Bảo tồn Di tích Cố đô Huế. "
        "An Định là cung điện riêng của vua Khải Định, tọa lạc bên bờ sông "
        "An Cựu, nay mang số 97 đường Phan Đình Phùng, Thành phố Huế. "
        "Tên tiếng Anh thường dùng là An Dinh Palace."
    )
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


class IngestionPackageTests(unittest.TestCase):
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

    def test_incorrect_content_hash_is_rejected(self) -> None:
        package = valid_package()
        package["documents"][0]["content_hash"] = "not-the-raw-text-hash"
        with self.assertRaisesRegex(PackageValidationError, "content_hash"):
            validate_package(package)

    def test_invalid_observation_time_is_rejected(self) -> None:
        package = valid_package()
        package["documents"][0]["observed_at"] = "yesterday"
        with self.assertRaisesRegex(PackageValidationError, "observed_at"):
            validate_package(package)


if __name__ == "__main__":
    unittest.main()
