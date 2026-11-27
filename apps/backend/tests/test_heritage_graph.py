import unittest

from apps.backend.services.heritage_graph import (
    artifact_title_from_data, in_entity_follow_up, neighbor_follow_ups, ordered_entity_follow_ups,
    related_entity_titles,
)


class HeritageGraphTests(unittest.TestCase):
    def test_tu_duc_question_returns_complex_neighbors(self):
        titles = related_entity_titles("Lăng Tự Đức làm bằng gì?")
        self.assertEqual(titles, ["Bi Đình", "Điện Hòa Khiêm", "khu mộ vua Tự Đức"])

    def test_neighbor_questions_name_the_matched_area_not_a_hardcoded_alias(self):
        questions = neighbor_follow_ups("Lăng Tự Đức làm bằng gì?")
        self.assertTrue(all("Lăng Tự Đức" in item for item in questions))
        self.assertTrue(all("Khiêm Lăng" not in item for item in questions))
        self.assertTrue(any("Bi Đình" in item for item in questions))
        self.assertTrue(any("Hòa Khiêm" in item for item in questions))

    def test_first_question_stays_with_the_specific_entity(self):
        self.assertEqual(
            in_entity_follow_up("Bi Đình trong Lăng Tự Đức có gì đặc biệt?", area_title="Lăng Tự Đức"),
            "Lịch sử của Bi Đình trong Lăng Tự Đức có gì đáng chú ý?",
        )
        self.assertEqual(
            in_entity_follow_up("Lịch sử của Bi Đình trong Lăng Tự Đức có gì đáng chú ý?", area_title="Lăng Tự Đức"),
            "Bi Đình trong Lăng Tự Đức gắn với nhân vật hoặc sự kiện nào?",
        )

    def test_selected_point_takes_priority_without_inventing_an_artifact(self):
        self.assertEqual(
            in_entity_follow_up("Cổ vật này có gì đặc biệt?", area_title="Lăng Tự Đức", focus_title="Bia Khiêm Cung Ký"),
            "Lịch sử của Bia Khiêm Cung Ký trong Lăng Tự Đức có gì đáng chú ý?",
        )
        self.assertEqual(
            in_entity_follow_up("Cung An Định được xây thế nào?", area_title="Cung An Định"),
            "Lịch sử của Cung An Định có gì đáng chú ý?",
        )
        self.assertIsNone(in_entity_follow_up("Chào bạn"))


    def test_follow_up_pair_orders_entity_then_neighbor_and_skips_the_asked_question(self):
        asked = "Bi Đình trong Lăng Tự Đức có gì đặc biệt?"
        self.assertEqual(ordered_entity_follow_ups(asked, area_title="Lăng Tự Đức"), [
            "Lịch sử của Bi Đình trong Lăng Tự Đức có gì đáng chú ý?",
            "Điện Hòa Khiêm trong Lăng Tự Đức có gì đặc biệt?",
        ])
        repeated = "Lịch sử của Bi Đình trong Lăng Tự Đức có gì đáng chú ý?"
        again = ordered_entity_follow_ups(repeated, area_title="Lăng Tự Đức")
        self.assertNotIn(repeated, again)
        self.assertEqual(again[0], "Bi Đình trong Lăng Tự Đức gắn với nhân vật hoặc sự kiện nào?")
        self.assertIn("Điện Hòa Khiêm", again[1])

    def test_missing_artifact_data_asks_about_the_entity_without_inventing_a_name(self):
        self.assertIsNone(artifact_title_from_data(
            focus_title="Điểm đang chọn",
            graph_context=[{"kind": "entity", "type": "place", "title": "Bia Khiêm Cung Ký"}],
            evidence=[type("Evidence", (), {"text": "Bia Khiêm Cung Ký", "artifact_title": None})()],
        ))
        questions = ordered_entity_follow_ups("Lăng Tự Đức làm bằng gì?", area_title="Lăng Tự Đức")
        self.assertEqual(questions, [
            "Lịch sử của Lăng Tự Đức có gì đáng chú ý?",
            "Bi Đình trong Lăng Tự Đức có gì đặc biệt?",
        ])
        self.assertNotIn("Bia Khiêm Cung Ký", " ".join(questions))

    def test_identified_artifact_leads_unless_the_question_names_another_part(self):
        self.assertEqual(artifact_title_from_data(
            graph_context=[{"kind": "entity", "type": "artifact", "title": "Bia Khiêm Cung Ký"}],
        ), "Bia Khiêm Cung Ký")
        self.assertEqual(ordered_entity_follow_ups(
            "Lăng Tự Đức làm bằng gì?", area_title="Lăng Tự Đức", artifact_title="Bia Khiêm Cung Ký",
        ), [
            "Lịch sử của Bia Khiêm Cung Ký trong Lăng Tự Đức có gì đáng chú ý?",
            "Bi Đình trong Lăng Tự Đức có gì đặc biệt?",
        ])
        part = ordered_entity_follow_ups(
            "Bi Đình trong Lăng Tự Đức có gì đặc biệt?", area_title="Lăng Tự Đức",
            artifact_title="Bia Khiêm Cung Ký",
        )
        self.assertEqual(part[0], "Lịch sử của Bi Đình trong Lăng Tự Đức có gì đáng chú ý?")
        self.assertNotIn("Bia Khiêm Cung Ký", part[0])


    def test_unrelated_question_has_no_neighbors(self):
        self.assertEqual(related_entity_titles("Giá bitcoin hôm nay bao nhiêu?"), [])
        self.assertEqual(neighbor_follow_ups("Giá bitcoin hôm nay bao nhiêu?"), [])

    def test_part_question_points_back_to_the_hub(self):
        titles = related_entity_titles("Bi Đình dùng để làm gì?")
        self.assertIn("Lăng Tự Đức", titles)
        self.assertNotIn("Khiêm Lăng", titles)

    def test_registered_areas_are_hubs_without_invented_parts(self):
        from apps.backend.services.heritage_graph import heritage_graph
        from apps.backend.services.tour_scope import AREAS

        graph = heritage_graph()
        self.assertTrue(all(area.id in graph for area in AREAS))
        self.assertEqual(related_entity_titles("Lăng Minh Mạng được xây thế nào?"), [])
        self.assertEqual(neighbor_follow_ups("Cung An Định có gì đặc biệt?"), [])
        self.assertEqual(
            related_entity_titles("Tháp Phước Duyên nằm ở đâu?"),
            ["Chùa Thiên Mụ"],
        )
        self.assertEqual(
            neighbor_follow_ups("Chùa Thiên Mụ có gì nổi bật?"),
            ["Tháp Phước Duyên trong Chùa Thiên Mụ có gì đặc biệt?"],
        )
        self.assertNotIn("Khiêm Lăng", " ".join(neighbor_follow_ups("Ứng Lăng của ai?")))



if __name__ == "__main__":
    unittest.main()
