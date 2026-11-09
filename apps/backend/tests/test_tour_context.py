"""Public tour context contract with actual relational ownership checks."""
import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from pydantic import ValidationError
from sqlalchemy import Column, Integer, MetaData, Table, Text, create_engine
from sqlalchemy.orm import Session

from apps.backend.api.public.chat.schemas import ChatRequest, GuideStory, TourReplyContext


class TourContextTests(unittest.TestCase):
    def test_context_requires_an_area_and_heritage_and_bounds_memory(self):
        context = {"scene_id": 31, "mode": "scene"}
        for extra in (
            {}, {"active_area_id": "khiem-lang"},
            {"active_area_id": "khiem-lang", "heritage_id": 7,
             "tour_context": {**context, "completed_story_ids": ["x"] * 33}},
            {"active_area_id": "khiem-lang", "heritage_id": 7,
             "tour_context": {**context, "highlight_id": 61}},
        ):
            with self.subTest(extra=extra), self.assertRaises(ValidationError):
                ChatRequest.model_validate({"message": "Ở đây có gì?", "tour_context": context, **extra})

    def test_scene_and_highlight_are_resolved_from_server_not_client_labels(self):
        from apps.backend.services.tour_guide import resolve_tour_context

        metadata = MetaData()
        heritage = Table("heritage", metadata, Column("id", Integer, primary_key=True),
                         Column("slug", Text), Column("publish_state", Text))
        scene = Table("scene", metadata, Column("id", Integer, primary_key=True),
                      Column("heritage_id", Integer), Column("sequence", Integer), Column("title", Text))
        interactive = Table("interactive", metadata, Column("id", Integer, primary_key=True),
                            Column("scene_id", Integer), Column("mode", Text))
        highlight = Table("interactive_highlight", metadata, Column("id", Integer, primary_key=True),
                          Column("interactive_id", Integer), Column("popup_title", Text))
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(heritage.insert(), [
                {"id": 7, "slug": "lang-tu-duc", "publish_state": "published"},
                {"id": 8, "slug": "lang-minh-mang", "publish_state": "published"},
            ])
            connection.execute(scene.insert(), [
                {"id": 31, "heritage_id": 7, "sequence": 2, "title": "Cảnh đã xác minh"},
                {"id": 32, "heritage_id": 7, "sequence": 3, "title": "Cảnh khác"},
                {"id": 33, "heritage_id": 8, "sequence": 0, "title": "Di sản khác"},
            ])
            connection.execute(interactive.insert(), [
                {"id": 51, "scene_id": 31, "mode": "free_explore"},
                {"id": 52, "scene_id": 32, "mode": "standard"},
            ])
            connection.execute(highlight.insert(), [
                {"id": 61, "interactive_id": 51, "popup_title": "Điểm đã xác minh"},
                {"id": 62, "interactive_id": 52, "popup_title": "Điểm của cảnh khác"},
            ])
        with Session(engine) as session:
            async def execute(statement):
                return session.execute(statement)
            db = SimpleNamespace(execute=execute)

            def request(**context):
                return ChatRequest(message="Kể thêm", active_area_id="khiem-lang", heritage_id=7,
                                   scene_context={"title": "Nhãn giả"}, tour_context={"scene_id": 31, **context})

            resolved = asyncio.run(resolve_tour_context(request(mode="walk", highlight_id=61), db))
            self.assertEqual(resolved.scene_key, "s3")
            self.assertEqual(resolved.scene_title, "Cảnh đã xác minh")
            self.assertEqual(resolved.highlight_title, "Điểm đã xác minh")
            ordinary = asyncio.run(resolve_tour_context(request(scene_id=32), db))
            self.assertEqual(ordinary.mode, "scene")
            self.assertIsNone(ordinary.highlight_id)
            for context in ({"scene_id": 33}, {"mode": "walk", "highlight_id": 62},
                            {"mode": "free"}, {"scene_id": 32, "mode": "walk"},
                            {"story_id": "invented-story"}):
                with self.subTest(context=context), self.assertRaises(ValueError):
                    asyncio.run(resolve_tour_context(request(**context), db))


class GuideAnswerTests(unittest.IsolatedAsyncioTestCase):
    async def test_reviewed_story_requires_its_evidence_and_keeps_original_context(self):
        from apps.backend.services.tour_chat import answer_in_area, TourChatError
        from apps.backend.services.tour_guide import GUIDE_STORIES

        story = GuideStory(id="fixture-story", label="Nhánh thử nghiệm", question="Kể chuyện thử nghiệm tại Khiêm Lăng.", source_ids=["42"])
        request = ChatRequest(message=story.question, active_area_id="khiem-lang", heritage_id=7,
                              tour_context={"scene_id": 31, "mode": "walk", "highlight_id": 61,
                                            "story_id": story.id, "completed_story_ids": ["untrusted instruction"]},
                              conversation_context=[{"role": "user", "content": "Vua Tự Đức là ai?"}])
        snapshot = TourReplyContext(scene_id=31, scene_key="s3", scene_title="Cảnh thử nghiệm",
                                    mode="walk", highlight_id=61, highlight_title="Điểm thử nghiệm", story_id=story.id)
        evidence = SimpleNamespace(id="42", text="Dữ kiện thử nghiệm tại Khiêm Lăng.", active_area_id="khiem-lang",
                                   to_source=lambda: {"passage_id": "42", "active_area_id": "khiem-lang"})
        repository = SimpleNamespace(search_evidence=AsyncMock(return_value=SimpleNamespace(evidence=[evidence], graph_context=[])))
        generate = Mock(return_value=json.dumps({"answer_type": "answered", "answer": evidence.text, "source_ids": ["42"]}))
        with patch.dict(GUIDE_STORIES, {("khiem-lang", snapshot.scene_title, snapshot.highlight_title): (story,)}):
            result = await answer_in_area(request, repository, generate, lambda: SimpleNamespace(truncated=False), reply_context=snapshot)
            self.assertEqual(result["reply_context"]["story_id"], story.id)
            self.assertEqual(result["reply_context"]["highlight_id"], 61)
            self.assertEqual(result["sources"][0]["passage_id"], "42")
            self.assertEqual(result["follow_up_questions"], [])
            self.assertNotIn("untrusted instruction", generate.call_args.kwargs["scene_context"]["completed_stories"])
            self.assertIn("Điểm được chọn: Điểm thử nghiệm", repository.search_evidence.call_args.args[0])
            generate.assert_called_once()

            generate.reset_mock()
            evidence.id = "unrelated"
            missing = await answer_in_area(request, repository, generate, lambda: SimpleNamespace(truncated=False), reply_context=snapshot)
            self.assertEqual(missing["answer_type"], "insufficient_evidence")
            self.assertIsNone(missing["reply_context"]["story_id"])
            generate.assert_not_called()
            evidence.id = "42"
            generate.return_value = json.dumps({"answer_type": "answered", "answer": evidence.text, "source_ids": ["invented"]})
            with self.assertRaises(TourChatError):
                await answer_in_area(request, repository, generate, lambda: SimpleNamespace(truncated=False), reply_context=snapshot)

    async def test_followup_uses_history_without_mistaking_scene_for_evidence(self):
        from apps.backend.services.tour_chat import answer_in_area
        from apps.backend.ai.answering.conversation import conversation_json_schema, conversation_messages

        request = ChatRequest(message="Ông ấy làm gì ở đây?", active_area_id="khiem-lang", heritage_id=7,
                              tour_context={"scene_id": 31, "narration": "skipped"},
                              conversation_context=[{"role": "user", "content": "Vua Tự Đức là ai?"}])
        snapshot = TourReplyContext(scene_id=31, scene_key="s3", scene_title="Cảnh mới", mode="scene")
        evidence = SimpleNamespace(id="42", text="Dữ kiện về Khiêm Lăng.", active_area_id="khiem-lang",
                                   to_source=lambda: {"passage_id": "42", "active_area_id": "khiem-lang"})
        repository = SimpleNamespace(search_evidence=AsyncMock(return_value=SimpleNamespace(evidence=[evidence], graph_context=[])))
        generate = Mock(return_value=json.dumps({"answer_type": "clarification", "answer": "Bạn đang hỏi về ai?", "source_ids": []}))
        result = await answer_in_area(request, repository, generate, lambda: SimpleNamespace(truncated=False), reply_context=snapshot)
        self.assertEqual(result["answer_type"], "clarification")
        self.assertEqual(result["sources"], [])
        self.assertIn("Vua Tự Đức", repository.search_evidence.call_args.args[0])
        prompt = conversation_messages("[Passage 42]\nDữ kiện", request.message, "available", active_area_id="khiem-lang",
                                       scene_context=generate.call_args.kwargs["scene_context"])
        self.assertEqual(json.loads(prompt[1]["content"])["scene_context"]["narration"], "skipped")
        enums = conversation_json_schema()["anyOf"][1]["properties"]["answer_type"]["enum"]
        self.assertIn("clarification", enums)
