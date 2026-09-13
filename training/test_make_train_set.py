from __future__ import annotations

import unittest

from training.make_train_set import drop_leaked_valid_rows, quality_issue


def sample(question: str, answer: str, source: str = "Thông tin có thật") -> dict:
    return {
        "messages": [
            {"role": "system", "content": "rules"},
            {
                "role": "user",
                "content": f"Nguồn: {source}\n\nCâu hỏi: {question}",
            },
            {"role": "assistant", "content": answer},
        ]
    }


class TrainingDataQualityTest(unittest.TestCase):
    def test_rejects_chinese_characters_in_assistant_answer(self) -> None:
        row = sample("Làng nghề có gì?", "Nghề gốm瓷器 rất nổi tiếng.")

        self.assertEqual(quality_issue(row), "assistant chứa chữ Trung")

    def test_rejects_tourist_advice_question(self) -> None:
        row = sample(
            "Du khách đến tham quan Chùa Thiên Mụ cần lưu ý những gì?",
            "Du khách nên giữ trật tự.",
        )

        self.assertEqual(quality_issue(row), "câu hỏi tư vấn tham quan")

    def test_rejects_citation_that_is_not_verbatim_source(self) -> None:
        row = sample(
            "Di tích được xây khi nào?",
            "Di tích được xây năm 1800. [Nguồn: xây năm 1800 ... — https://example.com]",
            source="Di tích được xây năm 1800.",
        )

        self.assertEqual(quality_issue(row), "trích dẫn không có trong nguồn")

    def test_accepts_grounded_qa(self) -> None:
        row = sample(
            "Di tích được xây khi nào?",
            "Di tích được xây năm 1800. [Nguồn: Di tích được xây năm 1800. — https://example.com]",
            source="Di tích được xây năm 1800.",
        )

        self.assertIsNone(quality_issue(row))

    def test_drops_valid_source_seen_in_train_but_keeps_no_source_refusal(self) -> None:
        train = [sample("Câu train?", "Trả lời", source="Nguồn dùng chung")]
        shared = sample("Câu valid?", "Trả lời", source="Nguồn dùng chung")
        unique = sample("Câu khác?", "Trả lời", source="Nguồn chỉ valid")
        no_source = sample("Ngoài phạm vi?", "Không có thông tin", source="(không có)")

        kept, dropped = drop_leaked_valid_rows(train, [shared, unique, no_source])

        self.assertEqual(kept, [unique, no_source])
        self.assertEqual(dropped, 1)


if __name__ == "__main__":
    unittest.main()
