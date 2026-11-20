import unittest

from apps.backend.services.heritage_classifier import ContentInput, Prediction, classify, decision
from apps.backend.services.heritage_taxonomy import CATEGORIES, validate_categories


class HeritageClassifierTests(unittest.TestCase):
    def test_required_subjects_and_multiple_valid_categories(self):
        cases = (
            ("Ngũ Hành Sơn", "Ngũ Hành Sơn là một danh thắng gồm nhiều ngọn núi. Có lễ hội tại đây.", {"scenic_landscape"}),
            ("Chùa Thiên Mụ", "Ngôi chùa có nhiều cổ vật.", {"religious_site", "architecture"}),
            ("Cung An Định", "Có gắn với các nhân vật lịch sử.", {"architecture", "historical_site"}),
            ("Đại Nội Huế", "Nơi có lễ hội.", {"architecture", "historical_site"}),
            ("Bảo tàng Đà Nẵng", "Lưu giữ cổ vật, hiện vật và tư liệu.", {"museum"}),
            ("Bảo tàng Điêu khắc Chăm", "Trưng bày tượng và báu vật.", {"museum"}),
            ("Nhà Gươl A Ka", "Đây là không gian sinh hoạt cộng đồng.", {"architecture", "community_tradition"}),
        )
        for title, description, expected in cases:
            with self.subTest(title=title):
                prediction = classify(ContentInput(title=title, description=description))
                self.assertEqual(set(prediction.categories), expected)
                self.assertEqual(prediction.entity_type, "place")
                self.assertEqual(decision(prediction), "applied")

    def test_related_mentions_never_become_identity(self):
        for title in ("Bảo tàng Lịch sử", "Chùa A", "Cung B"):
            result = classify(ContentInput(title=title, description="Lễ hội với nghệ nhân và cổ vật, nhân vật lịch sử."))
            self.assertFalse({"festival", "artifact", "artisan", "historical_figure"} & set(result.categories))
        self.assertEqual(classify(ContentInput(title="Người thuyết minh A", description="Giới thiệu lịch sử.")).categories, ())

    def test_nonplaces_get_independent_subject_types(self):
        for title, kind, key in (("Lễ hội Quán Thế Âm", "event", "festival"),
                                 ("Cổ vật Bình gốm", "artifact", "artifact"),
                                 ("Nghệ nhân A", "person", "artisan"),
                                 ("Nghề làm gốm", "practice", "traditional_craft")):
            result = classify(ContentInput(title=title))
            self.assertEqual((result.entity_type, result.primary_category), (kind, key))

    def test_semantic_rejects_hallucinated_evidence_and_incidental_festivals(self):
        def model(_):
            return {"entity_type": "event", "categories": ["festival"], "primary_category": "festival",
                    "confidence": 1.0, "evidence": "Có lễ hội tại đây."}
        content = ContentInput(title="Một địa điểm", description="Có lễ hội tại đây.")
        self.assertEqual(classify(content, semantic=model).categories, ())
        def invented(_):
            return {"entity_type": "place", "categories": ["museum"], "primary_category": "museum",
                    "confidence": 0.99, "evidence": "Invented evidence"}
        self.assertEqual(classify(content, semantic=invented).categories, ())

    def test_semantic_failure_falls_back_without_fabricating_categories(self):
        def unavailable(_):
            raise RuntimeError("unavailable")
        self.assertEqual(classify(ContentInput(title="Unknown"), semantic=unavailable).categories, ())
        self.assertEqual(decision(Prediction()), "unclassified")
        self.assertEqual(decision(Prediction(categories=("museum",), confidence=0.7)), "review")
        with self.assertRaises(ValueError):
            decision(Prediction(), high=0.5, medium=0.8)

    def test_taxonomy_keys_and_entity_validation(self):
        self.assertEqual(len(CATEGORIES), 14)
        for kind, keys, primary in (("place", ["artifact"], "artifact"),
                                    ("place", ["museum", "museum"], "museum"),
                                    ("person", ["artisan"], "festival")):
            with self.assertRaises(ValueError):
                validate_categories(kind, keys, primary)

    def test_reviewed_identity_and_subject_evidence_clarify_ambiguous_names(self):
        result = classify(ContentInput(title="Bình số 01", entity_type_hint="artifact", source_url="https://example.org/source"))
        self.assertEqual(result.categories, ("artifact",))
        result = classify(ContentInput(title="Ngũ Hành Sơn", tagline="Danh thắng có nhiều lễ hội"))
        self.assertEqual(result.categories, ("scenic_landscape",))
        result = classify(ContentInput(title="Một địa điểm", tagline="Lễ hội được tổ chức hàng năm"))
        self.assertEqual(result.categories, ())
        result = classify(ContentInput(title="Di sản A", reviewed_context="Di sản A là một bảo tàng được ghi nhận."))
        self.assertEqual(result.categories, ("museum",))
