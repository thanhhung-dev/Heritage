import unittest
from unittest.mock import AsyncMock, patch

from apps.backend.api.chat import ChatRequest, chat
from apps.backend.services.kg import Evidence


class DatabaseChatTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_evidence_fails_closed_without_generation(self) -> None:
        with (
            patch("apps.backend.api.chat._try_db_location_answer", AsyncMock(return_value=None)),
            patch("apps.backend.api.chat.KgRepository") as repository_type,
            patch("apps.backend.api.chat.generate_response") as generate_response,
        ):
            repository_type.return_value.search_evidence = AsyncMock(return_value=[])
            response = await chat(ChatRequest(message="không có dữ liệu"), AsyncMock())

        self.assertEqual(response.answer_type, "insufficient_evidence")
        self.assertEqual(response.resolution_status, "not_found")
        generate_response.assert_not_called()

    async def test_database_failure_is_controlled_without_generation(self) -> None:
        with (
            patch("apps.backend.api.chat._try_db_location_answer", AsyncMock(return_value=None)),
            patch("apps.backend.api.chat.KgRepository") as repository_type,
            patch("apps.backend.api.chat.generate_response") as generate_response,
        ):
            repository_type.return_value.search_evidence = AsyncMock(
                side_effect=ConnectionError("database unavailable")
            )
            response = await chat(ChatRequest(message="Cung An Định"), AsyncMock())

        self.assertEqual(response.resolution_status, "unavailable")
        generate_response.assert_not_called()

    async def test_generation_receives_only_database_evidence(self) -> None:
        evidence = Evidence(
            evidence_id="passage-uuid", evidence_type="passage", entity_id="entity-uuid",
            content="Đoạn trích có thật", source_title="Nguồn", source_url="https://example.org",
            tier=1, observed_at=None, retrieval_score=1.0, reason="lexical",
        )
        with (
            patch("apps.backend.api.chat._try_db_location_answer", AsyncMock(return_value=None)),
            patch("apps.backend.api.chat.KgRepository") as repository_type,
            patch("apps.backend.api.chat.generate_response", return_value="Trả lời") as generate_response,
        ):
            repository_type.return_value.search_evidence = AsyncMock(return_value=[evidence])
            response = await chat(ChatRequest(message="Cung An Định"), AsyncMock())

        self.assertEqual(response.sources[0]["passage_id"], "passage-uuid")
        generate_response.assert_called_once_with(
            question="Cung An Định", context="[passage-uuid] Đoạn trích có thật"
        )


if __name__ == "__main__":
    unittest.main()
