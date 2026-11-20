"""Public tour context contract with actual relational ownership checks."""
import asyncio
import json
import time
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
        Table("interactive_highlight_passage", metadata, Column("highlight_id", Integer, primary_key=True),
              Column("passage_id", Text, primary_key=True), Column("content_hash", Text),
              Column("object_key", Text), Column("bucket", Text))
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
    async def test_scene_affects_retrieval_only_for_context_dependent_questions(self):
        from apps.backend.services.tour_chat import answer_in_area

        scene_title = "Khiêm Lăng – Dấu ấn một đế vương"
        snapshot = TourReplyContext(scene_id=1, scene_key="s0", scene_title=scene_title, mode="scene")

        async def search(question, *, active_area_id):
            source = ("previous_topic" if "Câu hỏi trước" in question else
                      "scene" if scene_title in question else "overview")
            evidence = SimpleNamespace(
                id=source, text="Dữ kiện về Khiêm Lăng.", active_area_id=active_area_id,
                to_source=lambda: {"passage_id": source, "active_area_id": active_area_id},
            )
            return SimpleNamespace(evidence=[evidence], graph_context=[])

        def generate(*, question, context="", **kwargs):
            source = ("previous_topic" if "[Passage previous_topic]" in context else
                      "scene" if "[Passage scene]" in context else "overview")
            return json.dumps({"answer_type": "answered", "answer": "Dữ kiện về Khiêm Lăng.", "source_ids": [source]})

        for question, expected in (
            ("lăng tự đức là gì", "overview"),
            ("lang tu duc la gi", "overview"),
            ("bia khiêm cung ký có gì nhỉ , nó được làm bằng gì ?", "overview"),
            ("Khiêm Cung Môn có kiến trúc như thế nào?", "overview"),
            ("Lăng Tự Đức xây năm nào?", "overview"),
            ("Ở đây có gì?", "scene"),
            ("o day co gi?", "scene"),
            ("Công trình này là gì?", "scene"),
            ("Cảnh này có gì đặc biệt?", "scene"),
        ):
            for resolved in (False, True):
                with self.subTest(question=question, resolved=resolved):
                    request = ChatRequest(
                        message=question, active_area_id="khiem-lang", heritage_id=1,
                        scene_context={"title": scene_title},
                        tour_context={"scene_id": 1} if resolved else None,
                        conversation_context=[{"role": "user", "content": "Lăng Tự Đức ở đâu?"}],
                    )
                    result = await answer_in_area(
                        request, SimpleNamespace(search_evidence=search), generate,
                        lambda: SimpleNamespace(truncated=False), reply_context=snapshot if resolved else None,
                    )
                    self.assertEqual(result["answer_type"], "answered")
                    self.assertEqual(result["sources"][0]["passage_id"], expected)

    async def test_dialogue_question_keeps_the_model_conversation_answer(self):
        from apps.backend.ai.answering.conversation import conversation_messages
        from apps.backend.services.tour_chat import answer_in_area

        asked = "Tư liệu nào giải thích ý nghĩa của Bia Đá Và Những nỗi niềm khắc trên đá?"
        replied = "Bia Khiêm Cung Ký được soạn năm 1871."
        request = ChatRequest(
            message="nãy h tôi nói gì ấy nhỉ", active_area_id="khiem-lang", heritage_id=7,
            tour_context={"scene_id": 31, "mode": "walk", "highlight_id": 61},
            conversation_context=[
                {"role": "user", "content": asked},
                {"role": "assistant", "content": replied},
            ],
        )
        snapshot = TourReplyContext(
            scene_id=31, scene_key="s4", scene_title="Bia đá và những nỗi niềm", mode="walk",
            highlight_id=61, highlight_title="Bia Đá Và Những nỗi niềm khắc trên đá",
            passage_links={"42": {"content_hash": "hash", "object_key": "", "bucket": ""}},
        )
        repository = SimpleNamespace(search_evidence=AsyncMock(return_value=SimpleNamespace(
            evidence=[], graph_context=[],
        )))
        generate = Mock(return_value=json.dumps({
            "answer_type": "conversation", "answer": f"Bạn vừa hỏi: {asked}", "source_ids": [],
        }))
        result = await answer_in_area(
            request, repository, generate, lambda: SimpleNamespace(truncated=False), reply_context=snapshot,
        )
        self.assertEqual(result["answer_type"], "conversation")
        self.assertEqual(result["answer"], f"Bạn vừa hỏi: {asked}")
        self.assertEqual(result["sources"], [])
        self.assertEqual(generate.call_args.kwargs["dialogue"], [
            {"role": "user", "content": asked},
            {"role": "assistant", "content": replied},
        ])
        prompt = conversation_messages("passage", request.message, dialogue=generate.call_args.kwargs["dialogue"])
        self.assertEqual([item["role"] for item in prompt], ["system", "user", "assistant", "user"])
        self.assertIn(asked, prompt[1]["content"])
        self.assertIn(replied, prompt[2]["content"])
        self.assertIn("không phải bằng chứng lịch sử", prompt[0]["content"])

    async def test_reviewed_story_requires_its_evidence_and_keeps_original_context(self):
        from apps.backend.services.tour_chat import answer_in_area, TourChatError
        from apps.backend.services.tour_guide import GUIDE_STORIES

        story = GuideStory(id="fixture-story", label="Nhánh thử nghiệm", question="Kể chuyện thử nghiệm tại Khiêm Lăng.", source_ids=["42"])
        request = ChatRequest(message=story.question, active_area_id="khiem-lang", heritage_id=7,
                              tour_context={"scene_id": 31, "mode": "walk", "highlight_id": 61,
                                            "story_id": story.id, "completed_story_ids": ["untrusted instruction"]},
                              conversation_context=[{"role": "user", "content": "Vua Tự Đức là ai?"}])
        snapshot = TourReplyContext(scene_id=31, scene_key="s3", scene_title="Cảnh thử nghiệm",
                                    mode="walk", highlight_id=61, highlight_title="Điểm thử nghiệm", story_id=story.id,
                                    passage_links={"42": {"content_hash": "hash", "object_key": "", "bucket": ""}})
        evidence = SimpleNamespace(id="42", text="Dữ kiện thử nghiệm tại Khiêm Lăng.", active_area_id="lang-tu-duc",
                                   to_source=lambda: {"passage_id": "42", "active_area_id": "lang-tu-duc"})
        repository = SimpleNamespace(search_evidence=AsyncMock(return_value=SimpleNamespace(evidence=[evidence], graph_context=[])))
        generate = Mock(return_value=json.dumps({"answer_type": "answered", "answer": evidence.text, "source_ids": ["42"]}))
        with patch.dict(GUIDE_STORIES, {("lang-tu-duc", snapshot.scene_title, snapshot.highlight_title): (story,)}):
            result = await answer_in_area(request, repository, generate, lambda: SimpleNamespace(truncated=False), reply_context=snapshot)
            self.assertEqual(result["reply_context"]["story_id"], story.id)
            self.assertEqual(result["reply_context"]["highlight_id"], 61)
            self.assertEqual(result["sources"][0]["passage_id"], "42")
            self.assertGreaterEqual(len(result["follow_up_questions"]), 1)
            self.assertLessEqual(len(result["follow_up_questions"]), 3)
            self.assertEqual(generate.call_args.kwargs["user_history"], ["Vua Tự Đức là ai?"])
            self.assertIn("Điểm đang chọn: Điểm thử nghiệm", repository.search_evidence.call_args.args[0])
            self.assertEqual(generate.call_count, 1)
            self.assertTrue(generate.call_args.kwargs.get("conversation"))

            generate.reset_mock()
            evidence.id = "unrelated"
            missing = await answer_in_area(request, repository, generate, lambda: SimpleNamespace(truncated=False), reply_context=snapshot)
            self.assertEqual(missing["answer_type"], "insufficient_evidence")
            self.assertIsNone(missing["reply_context"]["story_id"])
            generate.assert_not_called()
            evidence.id = "42"
            generate.return_value = json.dumps({"answer_type": "answered", "answer": evidence.text, "source_ids": ["invented"]})
            invented = await answer_in_area(request, repository, generate, lambda: SimpleNamespace(truncated=False), reply_context=snapshot)
            self.assertEqual(invented["answer_type"], "insufficient_evidence")

    async def test_followup_uses_history_without_a_second_model_call(self):
        from apps.backend.services.tour_chat import answer_in_area
        from apps.backend.ai.answering.conversation import conversation_json_schema, conversation_messages

        request = ChatRequest(message="Ông ấy làm gì ở đây?", active_area_id="khiem-lang", heritage_id=7,
                              tour_context={"scene_id": 31, "narration": "skipped"},
                              conversation_context=[{"role": "user", "content": "Vua Tự Đức là ai?"}])
        snapshot = TourReplyContext(scene_id=31, scene_key="s3", scene_title="Cảnh mới", mode="scene")
        evidence = SimpleNamespace(id="42", text="Dữ kiện về Khiêm Lăng.", active_area_id="lang-tu-duc",
                                   to_source=lambda: {"passage_id": "42", "active_area_id": "lang-tu-duc"})
        repository = SimpleNamespace(search_evidence=AsyncMock(return_value=SimpleNamespace(evidence=[evidence], graph_context=[])))
        generate = Mock(return_value=json.dumps({
            "answer_type": "answered", "answer": evidence.text, "source_ids": ["42"],
        }))
        result = await answer_in_area(request, repository, generate, lambda: SimpleNamespace(truncated=False), reply_context=snapshot)
        self.assertEqual(result["answer_type"], "answered")
        self.assertEqual(
            repository.search_evidence.call_args.args[0],
            "Câu hỏi trước của người dùng: Vua Tự Đức là ai?\nCâu hỏi hiện tại: Ông ấy làm gì ở đây?"
            "\nCảnh đang xem: Cảnh mới",
        )
        self.assertEqual(generate.call_count, 1)
        self.assertEqual(generate.call_args.kwargs["question"], request.message)
        self.assertEqual(generate.call_args.kwargs["user_history"], ["Vua Tự Đức là ai?"])
        prompt = conversation_messages(
            "[Passage 42]\nDữ kiện", request.message, "available",
            active_area_id="khiem-lang", user_history=["Vua Tự Đức là ai?"],
        )
        self.assertEqual([item["role"] for item in prompt], ["system", "user", "user"])
        self.assertEqual(prompt[1]["content"], "Vua Tự Đức là ai?")
        self.assertIn("Câu hỏi: Ông ấy làm gì ở đây?", prompt[-1]["content"])
        self.assertNotIn("LỊCH SỬ CÂU HỎI", prompt[-1]["content"])
        self.assertEqual(
            set(conversation_json_schema()["required"]),
            {"answer_type", "answer", "source_ids"},
        )

    async def test_resolution_retrieval_and_answer_share_one_deadline(self):
        from apps.backend.services.tour_chat import TourChatError, answer_in_area

        request = ChatRequest(message="Nó làm bằng gì?", active_area_id="khiem-lang",
                              conversation_context=[{"role": "user", "content": "Tôi hỏi về nhà bia."}])
        evidence = SimpleNamespace(id="42", text="Dữ kiện có nguồn.", active_area_id="lang-tu-duc",
                                   to_source=lambda: {"passage_id": "42", "active_area_id": "lang-tu-duc"})

        async def search(*args, **kwargs):
            await asyncio.sleep(.04)
            return SimpleNamespace(evidence=[evidence], graph_context=[])

        def generate(**kwargs):
            time.sleep(.04)
            return json.dumps({"answer_type": "answered", "answer": evidence.text, "source_ids": ["42"]})

        for budget in (.05, 1):
            with self.subTest(budget=budget), patch("apps.backend.services.tour_chat.chat_timeout_seconds", return_value=budget):
                if budget == .05:
                    with self.assertRaises(TourChatError) as raised:
                        await answer_in_area(request, SimpleNamespace(search_evidence=search), generate,
                                             lambda: SimpleNamespace(truncated=False))
                    self.assertEqual(raised.exception.status, 504)
                else:
                    result = await answer_in_area(request, SimpleNamespace(search_evidence=search), generate,
                                                  lambda: SimpleNamespace(truncated=False))
                    self.assertEqual(result["sources"], [{"passage_id": "42", "active_area_id": "lang-tu-duc"}])


    async def test_selected_badge_keeps_partial_answers_grounded_and_deselection_returns_to_p1(self):
        from apps.backend.services.tour_chat import answer_in_area

        a = SimpleNamespace(id="a-source", text="Bia Khiêm Cung Ký do Tự Đức soạn nội dung.",
                            active_area_id="lang-tu-duc",
                            to_source=lambda: {"passage_id": "a-source", "active_area_id": "lang-tu-duc"})
        b = SimpleNamespace(id="b-source", text="Dữ kiện về một điểm khác.", active_area_id="lang-tu-duc",
                            to_source=lambda: {"passage_id": "b-source", "active_area_id": "lang-tu-duc"})
        repository = SimpleNamespace(search_evidence=AsyncMock(return_value=SimpleNamespace(
            evidence=[a, b], graph_context=[])))
        snapshot = TourReplyContext(scene_id=31, scene_key="s3", scene_title="Cảnh bia",
                                    mode="standard", highlight_id=61, highlight_title="Bia Khiêm Cung Ký",
                                    passage_links={"a-source": {"content_hash": "hash", "object_key": "", "bucket": ""}})
        request = ChatRequest(message="Ai khắc chữ trên bia?", active_area_id="lang-tu-duc", heritage_id=7,
                              tour_context={"scene_id": 31, "mode": "standard", "highlight_id": 61})
        generate = Mock(return_value=json.dumps({
            "answer_type": "answered", "source_ids": ["a-source"],
            "answer": "Chưa xác nhận ai khắc chữ; nguồn chỉ nói Tự Đức soạn nội dung."}))
        selected = await answer_in_area(request, repository, generate,
                                        lambda: SimpleNamespace(truncated=False), reply_context=snapshot)
        self.assertEqual([item["passage_id"] for item in selected["sources"]], ["a-source"])
        self.assertNotIn("b-source", generate.call_args.kwargs["context"])
        self.assertEqual(generate.call_args.kwargs["artifact_title"], "Bia Khiêm Cung Ký")
        self.assertEqual(repository.search_evidence.call_args.kwargs["passage_links"], snapshot.passage_links)

        repository.search_evidence.reset_mock()
        generate.return_value = json.dumps({"answer_type": "answered", "answer": b.text,
                                            "source_ids": ["b-source"]})
        deselected = await answer_in_area(request.model_copy(update={
            "tour_context": request.tour_context.model_copy(update={"highlight_id": None}),
        }), repository, generate, lambda: SimpleNamespace(truncated=False),
            reply_context=snapshot.model_copy(update={"highlight_id": None, "highlight_title": None,
                                               "passage_links": {}}))
        self.assertEqual([item["passage_id"] for item in deselected["sources"]], ["b-source"])
        self.assertEqual(repository.search_evidence.call_args.kwargs, {"active_area_id": "lang-tu-duc"})

    async def test_unlinked_marker_never_falls_back_even_for_a_plain_question(self):
        from apps.backend.services.tour_chat import answer_in_area

        repository = SimpleNamespace(search_evidence=AsyncMock())
        generate = Mock()
        request = ChatRequest(message="Ai soạn văn bia?", active_area_id="lang-tu-duc", heritage_id=7,
                              tour_context={"scene_id": 31, "mode": "standard", "highlight_id": 99})
        snapshot = TourReplyContext(scene_id=31, scene_key="s3", scene_title="Cảnh bia", mode="standard",
                                    highlight_id=99, highlight_title="Điểm chưa liên kết")
        locked = await answer_in_area(request, repository, generate,
                                      lambda: SimpleNamespace(truncated=False), reply_context=snapshot)
        self.assertEqual(locked["answer_type"], "insufficient_evidence")
        self.assertEqual(locked["sources"], [])
        self.assertEqual(locked["follow_up_questions"], [])
        repository.search_evidence.assert_not_awaited()
        generate.assert_not_called()



class FollowupRewriteTests(unittest.TestCase):
    def test_prior_users_exclude_assistant_answers(self):
        from apps.backend.ai.answering.conversation import (
            prior_user_questions, rewrite_followup, rewrite_messages, standalone_question,
        )

        history = [
            {"role": "user", "content": "mộ được làm bằng gì"},
            {"role": "assistant", "content": "Mộ bằng gạch và đá."},
        ]
        self.assertEqual(prior_user_questions(history), ["mộ được làm bằng gì"])
        prompt = rewrite_messages("bia á?", ["mộ được làm bằng gì"])[-1]["content"]
        self.assertIn("mộ được làm bằng gì", prompt)
        self.assertIn("Câu hỏi cuối: bia á?", prompt)
        self.assertNotIn("gạch", prompt)
        self.assertEqual(standalone_question('{"answer": "x"}', "bia á?"), "bia á?")
        self.assertEqual(
            standalone_question("Bia trong di sản này được làm bằng gì?", "bia á?"),
            "Bia trong di sản này được làm bằng gì?",
        )
        self.assertEqual(
            rewrite_followup("bia á?", history, lambda **kwargs: "Bia được làm bằng gì?"),
            "Bia được làm bằng gì?",
        )
        self.assertEqual(rewrite_followup("bia á?", history, lambda **kwargs: (_ for _ in ()).throw(RuntimeError())), "bia á?")
        self.assertEqual(rewrite_followup("bia á?", [], lambda **kwargs: (_ for _ in ()).throw(AssertionError())), "bia á?")
