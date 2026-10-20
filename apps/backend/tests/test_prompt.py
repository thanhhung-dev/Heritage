import unittest

from apps.backend.core.prompt import SYSTEM, chat_messages


class OverviewPromptTests(unittest.TestCase):
    def test_overview_requests_have_structured_depth_guidance(self):
        messages = chat_messages("Chùa Thiên Mụ được xây dựng năm 1601.", "Giới thiệu tổng quan về chùa Thiên Mụ.")
        system = messages[0]["content"]

        self.assertIn("câu hỏi giới thiệu, tổng quan hoặc lịch sử", system)
        self.assertIn("Khái quát", system)
        self.assertIn("Không trả lời chỉ bằng một câu", system)


if __name__ == "__main__":
    unittest.main()
