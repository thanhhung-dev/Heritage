"""Context and evidence stay distinct throughout follow-up generation."""
import unittest

from apps.backend.ai.answering.conversation import conversation_json_schema, conversation_messages


class ChatContextRegressionTests(unittest.TestCase):
    def test_each_evidence_id_remains_attached_to_its_text(self):
        context = "[Passage 42]\nBia Khiêm Cung Ký tại Bi Đình.\n\n[Passage 91]\nTư liệu thứ hai."
        prompt = conversation_messages(context, "Đây là bia Khiêm Cung Ký à?")
        for source_id in conversation_json_schema(context)["properties"]["source_ids"]["items"]["enum"]:
            self.assertIn(f"[Passage {source_id}]", prompt[-1]["content"])
        self.assertIn(context, prompt[-1]["content"])

    def test_followup_retains_both_roles_and_subject_beyond_old_summary_limit(self):
        history = [
            {"role": "user", "content": "Đây là cái gì?"},
            {"role": "assistant", "content": "Giới thiệu. " * 30 + "Đây là bia Khiêm Cung Ký."},
        ]
        for question in ("Chứ đây không là bia Khiêm Cung Ký à?", "Nó do ai soạn?", "Còn điện Hòa Khiêm thì sao?"):
            with self.subTest(question=question):
                prompt = conversation_messages("[Passage 42]\nTư liệu", question, dialogue=history)
                self.assertEqual(prompt[1:3], history)
                self.assertIn(question, prompt[-1]["content"])
                self.assertIn("không phải bằng chứng lịch sử", prompt[0]["content"])

    def test_recall_preserves_dialogue_but_does_not_turn_it_into_evidence(self):
        history = [{"role": "user", "content": "Tôi vừa hỏi về bia."}]
        prompt = conversation_messages("", "Tôi vừa hỏi gì?", dialogue=history)
        self.assertEqual(prompt[1], history[0])
        self.assertIn("không dùng Passage", prompt[-1]["content"])

    def test_verified_view_context_is_separate_from_evidence(self):
        prompt = conversation_messages(
            "[Passage 42]\nBia Khiêm Cung Ký.", "Đây là gì?",
            viewing_context='{"scene_title": "Bi Đình", "highlight_title": "Bia Khiêm Cung Ký"}',
        )
        self.assertIn("Bi Đình", prompt[0]["content"])
        self.assertIn("không thay thế Passage", prompt[0]["content"])
        self.assertNotIn("scene_title", prompt[-1]["content"])
