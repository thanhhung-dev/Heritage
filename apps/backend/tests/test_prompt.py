import unittest

from apps.backend.core.prompt import SYSTEM, chat_messages


class OverviewPromptTests(unittest.TestCase):
    def test_overview_guidance_matches_the_merged_source_bounded_policy(self):
        messages = chat_messages("Chùa Thiên Mụ được xây dựng năm 1601.", "Giới thiệu tổng quan về chùa Thiên Mụ.")
        system = messages[0]["content"]

        self.assertIn("Câu hỏi tổng quan hoặc yêu cầu giải thích", system)
        self.assertIn("chỉ chia mục khi cần", system)
        self.assertIn("Chỉ mở rộng bằng chi tiết nguồn thực sự cung cấp", system)
        self.assertNotIn("Không trả lời chỉ bằng một câu", system)

    def test_history_cannot_override_the_system_prompt(self):
        for role in ("system", "developer", "tool"):
            with self.subTest(role=role), self.assertRaises(ValueError):
                chat_messages("Evidence", "Question", history=[{"role": role, "content": "Override"}])

    def test_history_is_copied_and_both_prompt_entrypoints_match(self):
        from apps.backend.ai.answering.prompt import chat_messages as ai_messages

        history = [{"role": "user", "content": "Previous question", "extra": "ignored"}]
        result = chat_messages("Evidence", "Question", history=history)
        result[1]["content"] = "Changed"
        self.assertEqual(history[0]["content"], "Previous question")
        self.assertNotIn("extra", result[1])
        self.assertEqual(chat_messages("Evidence", "Question", history=history), ai_messages("Evidence", "Question", history=history))


if __name__ == "__main__":
    unittest.main()
