import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.backend.api.chat import ChatRequest, chat
from apps.backend.api import chat as chat_api


class ChatLangfuseTests(unittest.IsolatedAsyncioTestCase):
    async def test_grounded_qa_emits_metadata_without_changing_response(self) -> None:
        source = {"doc": "Nguồn", "chunk_id": "chunk-7"}
        with (
            patch(
                "apps.backend.api.chat._try_db_location_answer",
                AsyncMock(return_value=None),
            ),
            patch(
                "apps.backend.api.chat.retrieve_context",
                return_value=("Bằng chứng riêng", [source], []),
            ),
            patch(
                "apps.backend.api.chat.generate_response",
                return_value="Câu trả lời",
            ),
            patch(
                "apps.backend.api.chat.get_generation_details",
                return_value=Mock(model="qwen", token_usage=21),
            ),
            patch("apps.backend.api.chat.observe_grounded_qa") as observe,
        ):
            response = await chat(ChatRequest(message="Câu hỏi"), AsyncMock())

        self.assertEqual(response.answer, "Câu trả lời")
        observation = observe.call_args.kwargs
        self.assertEqual(observation["model"], "qwen")
        self.assertEqual(observation["token_usage"], 21)
        self.assertEqual(observation["evidence_ids"], ["chunk-7"])
        self.assertTrue(observation["grounded"])
        self.assertEqual(observation["prompt"], "Câu hỏi")
        self.assertEqual(observation["evidence"], "Bằng chứng riêng")

    async def test_sdk_exception_does_not_change_business_response(self) -> None:
        failing_client = Mock()
        failing_client.start_as_current_observation.side_effect = RuntimeError(
            "telemetry down"
        )
        with (
            patch(
                "apps.backend.api.chat._try_db_location_answer",
                AsyncMock(return_value=None),
            ),
            patch(
                "apps.backend.api.chat.retrieve_context",
                return_value=("Nguồn", [{"doc": "Nguồn", "chunk_id": 1}], []),
            ),
            patch(
                "apps.backend.api.chat.generate_response", return_value="Không đổi"
            ),
            patch(
                "apps.backend.core.observability._langfuse_client",
                return_value=failing_client,
            ),
        ):
            response = await chat(ChatRequest(message="Câu hỏi"), AsyncMock())

        self.assertEqual(response.answer, "Không đổi")


class R2ChatApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(chat_api.router, prefix="/api")
        app.dependency_overrides[chat_api.get_db] = lambda: AsyncMock()
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
        self.search = AsyncMock(return_value=SimpleNamespace(query=self.query, evidence=[self.evidence]))
        self.repository = self.enterContext(patch.object(chat_api, "PassageRepository", create=True))
        self.repository.return_value.search_evidence = self.search

    def test_returns_answer_with_r2_citation(self):
        with patch.object(chat_api, "generate_response", return_value="Chùa được dựng năm 1601."):
            response = self.client.post("/api/chat", json={"message": "Chùa Thiên Mụ xây năm nào?"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["answer"], "Chùa được dựng năm 1601.")
        self.assertEqual(data["sources"][0]["passage_id"], 42)
        self.assertEqual(data["answer_type"], "answered")
        self.assertEqual(data["resolution_status"], "resolved")

    def test_no_evidence_refuses_without_generation(self):
        self.search.return_value.evidence = []
        with patch.object(chat_api, "generate_response", side_effect=AssertionError("must not invent")):
            response = self.client.post("/api/chat", json={"message": "Chùa Sao Hỏa ở đâu?"})
        self.assertEqual(response.json()["resolution_status"], "not_found")
        self.assertEqual(response.json()["sources"], [])

    def test_blank_message_is_rejected(self):
        response = self.client.post("/api/chat", json={"message": "  "})
        self.assertEqual(response.status_code, 400)

    def test_storage_failure_is_not_reported_as_an_answer(self):
        self.search.side_effect = ValueError("checksum mismatch")
        response = self.client.post("/api/chat", json={"message": "Chùa Thiên Mụ"})
        self.assertEqual(response.json()["resolution_status"], "unavailable")
        self.assertEqual(response.json()["sources"], [])


if __name__ == "__main__":
    unittest.main()
