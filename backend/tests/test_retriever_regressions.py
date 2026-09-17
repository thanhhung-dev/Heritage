import unittest

from backend.core.corpus import load_docs
from backend.core.rag import retrieve_context
from backend.core.retriever import get_retriever


class RetrieverRegressionTests(unittest.TestCase):
    def test_general_place_question_includes_the_actual_article_lead(self):
        context, sources, _ = retrieve_context("kể chi tiết về ngũ hành sơn!")

        self.assertTrue(context.startswith("Ngũ Hành Sơn (chữ Hán: 五行山)"))
        self.assertTrue(
            any(
                source["chunk_id"] == "Ngũ Hành Sơn#0"
                and source["used_in_context"]
                for source in sources
            )
        )

    def test_coastal_city_paraphrase_ranks_song_han_first(self):
        result = get_retriever().retrieve(
            "con sông chia đôi thành phố biển miền Trung",
            top_k=3,
        )

        self.assertEqual(result["hits"][0]["doc"], "Sông Hàn")

    def test_noodle_paraphrase_is_accepted_as_in_domain(self):
        query = "món mì nào của phố cổ Hội An"

        result = get_retriever().retrieve(query, top_k=3)
        context, _, _ = retrieve_context(query)

        self.assertEqual(result["hits"][0]["doc"], "Cao lầu")
        self.assertTrue(result["anchored"])
        self.assertTrue(context)

    def test_wrong_location_type_is_confidently_corrected(self):
        query = "Lăng An Định ở đâu?"

        result = get_retriever().retrieve(query, top_k=3)
        context, _, corrections = retrieve_context(query)

        self.assertEqual(corrections[0]["original"], "Lăng An Định")
        self.assertEqual(corrections[0]["suggested"], "Cung An Định")
        self.assertGreaterEqual(corrections[0]["score"], 0.9)
        self.assertEqual(result["hits"][0]["doc"], "Cung An Định")
        self.assertTrue(context.startswith("Cung An Định"))

    def test_correction_preserves_accents_when_question_mark_is_separate(self):
        query = "còn lăng an định ?"

        result = get_retriever().retrieve(query, top_k=3)
        context, _, corrections = retrieve_context(query)

        self.assertEqual(corrections[0]["original"], "lăng an định")
        self.assertEqual(result["query_used"], "còn Cung An Định ?")
        self.assertEqual(result["hits"][0]["doc"], "Cung An Định")
        self.assertTrue(context)

    def test_single_word_typo_is_confidently_corrected(self):
        query = "Ngũ Hành Xơn ở đâu?"

        result = get_retriever().retrieve(query, top_k=3)
        context, _, corrections = retrieve_context(query)

        self.assertEqual(corrections[0]["original"], "Ngũ Hành Xơn")
        self.assertEqual(corrections[0]["suggested"], "Ngũ Hành Sơn")
        self.assertGreaterEqual(corrections[0]["score"], 0.9)
        self.assertEqual(result["hits"][0]["doc"], "Ngũ Hành Sơn")
        self.assertTrue(context.startswith("Ngũ Hành Sơn"))

    def test_ambiguous_partial_name_requires_confirmation(self):
        query = "ngũ hành gì đó ở đâu?"

        _, _, corrections = retrieve_context(query)

        self.assertEqual(corrections[0]["suggested"], "Ngũ Hành Sơn")
        self.assertGreaterEqual(corrections[0]["score"], 0.7)
        self.assertLess(corrections[0]["score"], 0.9)

    def test_partial_name_does_not_absorb_question_words(self):
        _, _, corrections = retrieve_context("ngũ hành ở đâu á")

        self.assertEqual(corrections[0]["original"], "ngũ hành")
        self.assertEqual(corrections[0]["suggested"], "Ngũ Hành Sơn")

    def test_typo_correction_applies_to_every_supported_location(self):
        location_categories = {"Danh thắng", "Di tích lịch sử", "Làng nghề"}
        locations = [
            doc["name"] for doc in load_docs()[0]
            if doc["category"] in location_categories
        ]

        for location in locations:
            typo = location[:-1] + "x"
            with self.subTest(location=location, typo=typo):
                result = get_retriever().retrieve(f"{typo} ở đâu?", top_k=3)
                context, _, corrections = retrieve_context(f"{typo} ở đâu?")

                self.assertTrue(corrections)
                self.assertEqual(corrections[0]["suggested"], location)
                self.assertGreaterEqual(corrections[0]["score"], 0.9)
                self.assertEqual(result["hits"][0]["doc"], location)
                self.assertTrue(context)

    def test_wrong_location_type_uses_matching_proper_name_generically(self):
        cases = {
            "Chùa Thanh Hà ở đâu?": "Làng Thanh Hà",
            "Đền Hòn Chén ở đâu?": "Điện Hòn Chén",
            "Lăng Điện Hải ở đâu?": "Thành Điện Hải",
        }

        for query, expected in cases.items():
            with self.subTest(query=query):
                result = get_retriever().retrieve(query, top_k=3)
                context, _, corrections = retrieve_context(query)

                self.assertEqual(corrections[0]["suggested"], expected)
                self.assertGreaterEqual(corrections[0]["score"], 0.9)
                self.assertEqual(result["hits"][0]["doc"], expected)
                self.assertTrue(context)


if __name__ == "__main__":
    unittest.main()
