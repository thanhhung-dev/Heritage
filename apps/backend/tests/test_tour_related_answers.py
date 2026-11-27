"""Tour answers keep useful retrieved evidence when generation cannot use it."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from apps.backend.api.public.chat.schemas import ChatRequest, TourContext, TourReplyContext
from apps.backend.services.tour_chat import answer_in_area


class RelatedTourAnswerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.evidence = SimpleNamespace(
            id="42", text="Khiêm Lăng bắt đầu được xây dựng năm 1864.",
            active_area_id="lang-tu-duc",
            to_source=lambda: {"passage_id": "42", "active_area_id": "lang-tu-duc"},
        )
        self.request = ChatRequest(
            message="Lăng được xây từ năm nào đến năm nào?", active_area_id="lang-tu-duc",
        )

    async def answer(self, raw, *, evidence=None, truncated=False, reply_context=None):
        repository = SimpleNamespace(search_evidence=AsyncMock(return_value=SimpleNamespace(
            evidence=[self.evidence] if evidence is None else evidence, graph_context=[],
        )))
        generate = (Mock(side_effect=raw) if isinstance(raw, Exception)
                    else Mock(return_value=raw if isinstance(raw, str) else json.dumps(raw)))
        result = await answer_in_area(
            self.request, repository, generate,
            lambda: SimpleNamespace(truncated=truncated), reply_context=reply_context,
        )
        return result, repository, generate

    async def test_related_evidence_is_returned_even_when_model_cannot_answer(self):
        result, _, generate = await self.answer({
            "answer_type": "insufficient_evidence", "answer": "Không biết năm hoàn thành.",
            "source_ids": [],
        })
        self.assertEqual(result["answer_type"], "answered")
        self.assertIn("thông tin liên quan", result["answer"])
        self.assertIn(self.evidence.text, result["answer"])
        self.assertEqual(result["sources"], [self.evidence.to_source()])
        self.assertEqual(result["resolution_status"], "resolved")
        self.assertEqual(generate.call_count, 1)

    async def test_invalid_or_failed_generation_uses_source_not_model_claims(self):
        for raw, truncated in [
            ("not JSON", False),
            (RuntimeError("private model error"), False),
            ({"answer_type": "answered", "answer": "Hoàn thành năm 9999.", "source_ids": ["42"]}, True),
            ({"answer_type": "answered", "answer": "Hoàn thành năm 9999.", "source_ids": ["invented"]}, False),
            ({"answer_type": "answered", "answer": "Hoàn thành năm 9999.", "source_ids": []}, False),
        ]:
            with self.subTest(raw=raw, truncated=truncated):
                result, _, _ = await self.answer(raw, truncated=truncated)
                self.assertEqual(result["answer_type"], "answered")
                self.assertIn(self.evidence.text, result["answer"])
                self.assertEqual(result["sources"], [self.evidence.to_source()])
                self.assertNotIn("9999", result["answer"])
                self.assertNotIn("private model error", result["answer"])

    async def test_no_usable_evidence_still_abstains(self):
        raw = {"answer_type": "insufficient_evidence", "answer": "Chưa có dữ liệu.", "source_ids": []}
        foreign = SimpleNamespace(id="foreign", text="Dữ kiện của khu khác.", active_area_id="lang-minh-mang")
        for evidence in [[], [foreign]]:
            with self.subTest(evidence=evidence):
                result, _, _ = await self.answer(raw, evidence=evidence)
                self.assertEqual(result["answer_type"], "insufficient_evidence")
                self.assertEqual(result["sources"], [])

    async def test_excerpt_skips_navigation_and_keeps_safe_source_sentences(self):
        self.evidence.text += "\nNguồn: https://example.test\nĐi tiếp [tour khác](/content/other)."
        result, _, _ = await self.answer("invalid JSON")
        self.assertEqual(result["answer_type"], "answered")
        self.assertIn("1864", result["answer"])
        self.assertNotIn("https://", result["answer"])
        self.assertNotIn("/content/", result["answer"])

    async def test_selected_highlight_does_not_borrow_another_points_evidence(self):
        self.request = self.request.model_copy(update={
            "heritage_id": 1,
            "tour_context": TourContext(scene_id=5, mode="standard", highlight_id=5, narration="partial"),
        })
        snapshot = TourReplyContext(
            scene_id=5, scene_key="s4", scene_title="Bia đá", mode="standard",
            highlight_id=5, highlight_title="Bia Khiêm Cung Ký", passage_links={"42": {}},
        )
        other = SimpleNamespace(id="other", text="Thông tin điểm khác.", active_area_id="lang-tu-duc")
        result, _, _ = await self.answer("invalid JSON", evidence=[other], reply_context=snapshot)
        self.assertEqual(result["answer_type"], "insufficient_evidence")
        self.assertEqual(result["sources"], [])

    async def test_related_fallback_does_not_claim_to_complete_a_reviewed_story(self):
        snapshot = TourReplyContext(
            scene_id=1, scene_key="s0", scene_title="Khiêm Lăng", mode="scene",
            story_id="reviewed-story",
        )
        self.request = self.request.model_copy(update={
            "tour_context": TourContext(scene_id=1, narration="partial"),
        })
        result, _, _ = await self.answer("invalid JSON", reply_context=snapshot)
        self.assertEqual(result["answer_type"], "answered")
        self.assertIsNone(result["reply_context"]["story_id"])

    async def test_other_area_is_still_out_of_scope(self):
        self.request = self.request.model_copy(update={"message": "Lăng Minh Mạng có gì?"})
        result, repository, _ = await self.answer("invalid JSON")
        self.assertEqual(result["answer_type"], "out_of_scope")
        self.assertEqual(result["sources"], [])
        repository.search_evidence.assert_not_awaited()
