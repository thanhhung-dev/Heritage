import unittest

from apps.backend.services.heritage_graph import neighbor_follow_ups, related_entity_titles


class HeritageGraphTests(unittest.TestCase):
    def test_tu_duc_question_returns_complex_neighbors(self):
        titles = related_entity_titles("Lăng Tự Đức làm bằng gì?")
        self.assertEqual(titles, ["Bi Đình", "Điện Hòa Khiêm", "khu mộ vua Tự Đức"])

    def test_neighbor_questions_name_the_complex(self):
        questions = neighbor_follow_ups("Lăng Tự Đức làm bằng gì?")
        self.assertTrue(all("Khiêm Lăng" in item for item in questions))
        self.assertTrue(any("Bi Đình" in item for item in questions))
        self.assertTrue(any("Hòa Khiêm" in item for item in questions))

    def test_unrelated_question_has_no_neighbors(self):
        self.assertEqual(related_entity_titles("Giá bitcoin hôm nay bao nhiêu?"), [])
        self.assertEqual(neighbor_follow_ups("Giá bitcoin hôm nay bao nhiêu?"), [])

    def test_part_question_points_back_to_the_hub(self):
        titles = related_entity_titles("Bi Đình dùng để làm gì?")
        self.assertIn("Khiêm Lăng", titles)


if __name__ == "__main__":
    unittest.main()
