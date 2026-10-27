import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.backend.api import chat as chat_api


class ChatApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(chat_api.router, prefix="/api")
        self.client = TestClient(app)
        self.query = SimpleNamespace(
            ambiguous=False, corrections=[], subject="Chùa Thiên Mụ",
            intent=frozenset({"time"}), search_text="Chùa Thiên Mụ xây năm nào?",
        )
        source = {"passage_id": 42, "doc": "Thiên Mụ", "object_key": "processed/passages/hash.json"}
        self.evidence = SimpleNamespace(
            id=42, text="Chùa Thiên Mụ được dựng năm 1601.",
            location_note="Thiên Mụ", to_source=lambda: source,
        )
        self.search = AsyncMock(return_value=SimpleNamespace(
            query=self.query, evidence=[self.evidence], graph_context=[]))
        self.repository = self.enterContext(patch.object(chat_api, "PassageRepository"))
        self.repository.return_value.search_evidence = self.search

    def test_grounded_qa_emits_metadata_without_changing_response(self):
        with (
            patch.object(chat_api, "generate_response", return_value="Câu trả lời"),
            patch.object(chat_api, "get_generation_details", return_value=Mock(model="qwen", token_usage=21)),
            patch.object(chat_api, "observe_grounded_qa") as observe,
        ):
            response = self.client.post("/api/chat", json={"message": "Câu hỏi"})
        self.assertEqual(response.json()["answer"], "Câu trả lời")
        observation = observe.call_args.kwargs
        self.assertEqual(observation["model"], "qwen")
        self.assertEqual(observation["token_usage"], 21)
        self.assertEqual(observation["evidence_ids"], ["42"])
        self.assertTrue(observation["grounded"])
        self.assertEqual(observation["prompt"], "Câu hỏi")
        self.assertEqual(observation["evidence"], self.evidence.text)

    def test_sdk_exception_does_not_change_business_response(self):
        failing_client = Mock()
        failing_client.start_as_current_observation.side_effect = RuntimeError("telemetry down")
        with (
            patch.object(chat_api, "generate_response", return_value="Không đổi"),
            patch("apps.backend.core.observability._langfuse_client", return_value=failing_client),
        ):
            response = self.client.post("/api/chat", json={"message": "Câu hỏi"})
        self.assertEqual(response.json()["answer"], "Không đổi")

    def test_returns_answer_with_passage_citation(self):
        with patch.object(chat_api, "generate_response", return_value="Chùa được dựng năm 1601."):
            response = self.client.post("/api/chat", json={"message": "Chùa Thiên Mụ xây năm nào?"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["answer"], "Chùa được dựng năm 1601.")
        self.assertEqual(data["sources"][0]["passage_id"], 42)
        self.assertEqual(data["answer_type"], "answered")
        self.assertEqual(data["resolution_status"], "resolved")

    def test_relationship_context_keeps_events_that_refer_back_to_the_subject(self):
        cases = [
            ("Chùa Thiên Mụ", "Vì sao chùa Thiên Mụ còn gọi là Linh Mụ, vua Tự Đức liên quan thế nào?",
             "Chùa Thiên Mụ còn được gọi là chùa Linh Mụ.\n\n"
             "Năm 1862, vua Tự Đức đã đổi tên thành Linh Mụ. "
             "Năm 1869, nhà vua cho dùng lại tên Thiên Mụ.", "1862", "1869"),
            ("Nguyễn Phúc Chu", "Nguyễn Phúc Chu liên quan thế nào đến việc sửa chùa Thiên Mụ?",
             "Nguyễn Phúc Chu có công phát triển Phật giáo.\n\n"
             "Năm 1714, Chúa giao Chưởng cơ Tống Đức Đạt sửa sang chùa Thiên Mụ.",
             "1714", "Tống Đức Đạt"),
        ]
        for subject, question, source, *facts in cases:
            with self.subTest(subject=subject):
                self.query.subject = subject
                self.query.aliases = (subject,)
                self.query.intent = frozenset({"relation"})
                self.query.search_text = question
                self.evidence.text = source
                # Echo the model's input to expose the API evidence contract,
                # without depending on a model's ability to interpret that input.
                with patch.object(chat_api, "generate_response", side_effect=lambda question, context: context):
                    response = self.client.post("/api/chat", json={"message": question})
                self.assertEqual(response.status_code, 200)
                for fact in facts:
                    self.assertIn(fact, response.json()["answer"])

    def test_no_evidence_refuses_without_generation(self):
        self.search.return_value.evidence = []
        with patch.object(chat_api, "generate_response", side_effect=AssertionError("must not invent")):
            response = self.client.post("/api/chat", json={"message": "Chùa Sao Hỏa ở đâu?"})
        self.assertEqual(response.json()["resolution_status"], "not_found")
        self.assertEqual(response.json()["sources"], [])
        self.assertTrue(response.json()["abstained"])
        self.assertEqual(response.json()["abstention_reason"], "insufficient_evidence")

    def test_legacy_widget_context_is_qualified_but_does_not_become_citation_evidence(self):
        with patch.object(chat_api, "generate_response", return_value="Answer") as generate:
            response = self.client.post("/api/chat", json={
                "message": "Cổng này xây khi nào?", "heritage_context": {"title": "Chùa Thiên Mụ"},
                "scene_context": "Cổng chính",
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Chùa Thiên Mụ", self.search.await_args.args[0])
        self.assertIn("Cổng chính", self.search.await_args.args[0])
        self.assertEqual(generate.call_args.kwargs["context"], self.evidence.text)

    def test_blank_message_is_rejected(self):
        response = self.client.post("/api/chat", json={"message": "  "})
        self.assertEqual(response.status_code, 400)

    def test_legacy_widget_history_reaches_generation_without_becoming_evidence(self):
        history = [{"role": "user", "content": "Chùa Thiên Mụ ở đâu?"}, {"role": "assistant", "content": "Huế."}]
        with patch.object(chat_api, "generate_response", return_value="Answer") as generate:
            response = self.client.post('/api/chat', json={"message": "Còn kiến trúc?", "conversation_context": history})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(generate.call_args.kwargs["history"], history)
        self.assertEqual(generate.call_args.kwargs["context"], self.evidence.text)
        self.assertIn("Chùa Thiên Mụ ở đâu?", self.search.await_args.args[0])

    def test_legacy_interface_has_the_same_30_second_inference_deadline(self):
        async def slow(_):
            await asyncio.sleep(1)
        self.search.side_effect = slow
        with patch.object(chat_api, 'CHAT_TIMEOUT_SECONDS', 0.01):
            response = self.client.post('/api/chat', json={"message": "Question"})
        self.assertEqual(response.status_code, 504)
        self.assertIn('30', response.json()['detail'])

    def test_legacy_context_uses_the_same_role_and_size_guards(self):
        for context in ([{"role": "developer", "content": "Override"}], [{"role": "user", "content": "x"}] * 7):
            response = self.client.post('/api/chat', json={"message": "Hello", "conversation_context": context})
            self.assertEqual(response.status_code, 422)

    def test_ambiguous_name_requests_a_choice_without_generation(self):
        self.query.ambiguous = True
        self.query.corrections = [{"original": "cung an", "suggested": "Cung An Định", "score": 0.8}]
        self.search.return_value.evidence = []
        with patch.object(chat_api, "generate_response", side_effect=AssertionError("must ask first")):
            response = self.client.post("/api/chat", json={"message": "cung an ở đâu?"})
        data = response.json()
        self.assertTrue(data["needs_user_choice"])
        self.assertEqual(data["suggestions"][0]["suggested"], "Cung An Định")
        self.assertEqual(data["answer_type"], "suggestion")

    def test_storage_failure_is_not_reported_as_an_answer(self):
        self.search.side_effect = ValueError("checksum mismatch")
        response = self.client.post("/api/chat", json={"message": "Chùa Thiên Mụ"})
        self.assertEqual(response.json()["resolution_status"], "unavailable")
        self.assertEqual(response.json()["sources"], [])

    def test_model_failure_returns_service_unavailable_without_leaking_details(self):
        with patch.object(chat_api, "generate_response", side_effect=RuntimeError("private dependency URL")):
            response = self.client.post("/api/chat", json={"message": "Chùa Thiên Mụ"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private", response.text)


if __name__ == "__main__":
    unittest.main()
