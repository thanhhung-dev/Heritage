import asyncio
import importlib
import json
import os
import time
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from apps.backend.api import chat as chat_api
from apps.backend.core.search import SearchError
from apps.backend.services.passages import PassageRepository


@contextmanager
def patched_llama_http(**kwargs):
    mock = Mock(**kwargs)
    with (
        patch("apps.backend.core.llm.llama_http_post", mock),
        patch("apps.backend.ai.providers.llm.llama_http_post", mock),
    ):
        yield mock




def model_answer(text, answer_type="answered", source_ids=None, follow_up_questions=None):
    if source_ids is None:
        source_ids = ["42"] if answer_type == "answered" else []
    payload = {"answer_type": answer_type, "answer": text, "source_ids": source_ids}
    if follow_up_questions is not None:
        payload["follow_up_questions"] = follow_up_questions
    return json.dumps(payload)


class ChatApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(chat_api.router, prefix="/api")
        self.client = self.enterContext(TestClient(app))
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
            patch.object(chat_api, "generate_response", return_value=model_answer("Câu trả lời")),
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

    def test_conversation_has_no_citations_even_when_retrieval_returns_passages(self):
        for question in ("hi", "Bạn là ai?", "Cảm ơn"):
            for has_evidence in (True, False):
                with self.subTest(question=question, has_evidence=has_evidence):
                    self.search.return_value.evidence = [self.evidence] if has_evidence else []
                    with patch.object(chat_api, "generate_response") as generate:
                        response = self.client.post("/api/chat", json={"message": question})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["answer"], "Mình là trợ lý AI HeritageGraph.")
                    self.assertEqual(response.json()["answer_type"], "conversation")
                    self.assertEqual(response.json()["sources"], [])
                    generate.assert_not_called()

    def test_mixed_question_keeps_only_cited_sources(self):
        other = SimpleNamespace(id="91", text="Nguồn không được dùng.",
                                to_source=lambda: {"passage_id": "91"})
        self.search.return_value.evidence.append(other)
        question = "Hi, chùa Thiên Mụ xây năm nào?"
        with patch.object(chat_api, "generate_response", return_value=model_answer(
            "Chào bạn! Chùa được dựng năm 1601.")) as generate:
            response = self.client.post("/api/chat", json={"message": question})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer_type"], "answered")
        self.assertEqual([s["passage_id"] for s in response.json()["sources"]], [42])
        self.assertEqual(generate.call_args.kwargs["question"], question)
        self.assertIn("[Passage 42]", generate.call_args.kwargs["context"])

    def test_unsupported_or_malformed_model_output_is_not_published(self):
        for raw, status in (
            ("unstructured answer", 503),
            ("{}", 503),
            (model_answer("  ", source_ids=[]), 503),
            (model_answer("Bịa", source_ids=["999"]), 200),
            (model_answer("Bịa", source_ids=[]), 200),
        ):
            with self.subTest(raw=raw), patch.object(chat_api, "generate_response", return_value=raw):
                response = self.client.post("/api/chat", json={"message": "Thiên Mụ ở đâu?"})
                self.assertEqual(response.status_code, status)
                self.assertNotIn("Bịa", response.text)

    def test_conversation_survives_retrieval_failure(self):
        self.search.side_effect = SearchError("private dependency URL")
        with patch.object(chat_api, "generate_response") as generate:
            response = self.client.post("/api/chat", json={"message": "hi"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer_type"], "conversation")
        self.assertEqual(response.json()["sources"], [])
        generate.assert_not_called()
        self.assertNotIn("private", response.text)

    def test_sdk_exception_does_not_change_business_response(self):
        failing_client = Mock()
        failing_client.start_as_current_observation.side_effect = RuntimeError("telemetry down")
        with (
            patch.object(chat_api, "generate_response", return_value=model_answer("Không đổi")),
            patch("apps.backend.core.observability._langfuse_client", return_value=failing_client),
        ):
            response = self.client.post("/api/chat", json={"message": "Câu hỏi"})
        self.assertEqual(response.json()["answer"], "Không đổi")

    def test_returns_answer_with_passage_citation(self):
        with patch.object(chat_api, "generate_response", return_value=model_answer("Chùa được dựng năm 1601.")):
            response = self.client.post("/api/chat", json={"message": "Chùa Thiên Mụ xây năm nào?"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["answer"], "Chùa được dựng năm 1601.")
        self.assertEqual(data["sources"][0]["passage_id"], 42)
        self.assertEqual(data["answer_type"], "answered")
        self.assertEqual(data["resolution_status"], "resolved")

    def test_answered_turn_returns_deduped_follow_ups_without_the_current_question(self):
        with patch.object(chat_api, "generate_response", return_value=model_answer(
            "Lăng xây bằng gạch và đá.",
            follow_up_questions=[
                "Khiêm Lăng có hồ nước không?",
                "Lăng Tự Đức làm bằng gì?",
                "Khiêm Lăng có hồ nước không?",
                "Xem https://evil.test",
                "Bi Đình dùng để làm gì?",
            ],
        )):
            response = self.client.post("/api/chat", json={"message": "Lăng Tự Đức làm bằng gì?"})
        self.assertEqual(response.status_code, 200, response.text)
        follow = response.json()["follow_up_questions"]
        self.assertGreaterEqual(len(follow), 2)
        self.assertLessEqual(len(follow), 3)
        self.assertNotIn("Lăng Tự Đức làm bằng gì?", follow)
        self.assertTrue(any("Bi Đình" in item for item in follow))
        self.assertTrue(any("Hòa Khiêm" in item for item in follow))

    def test_graph_topics_steer_follow_ups_without_requiring_citations(self):
        self.search.return_value.graph_context = [
            {"kind": "entity", "title": "Bi Đình", "source_passage_ids": ["42"]},
            {"kind": "relationship", "source": "Tự Đức", "target": "Khiêm Lăng",
             "source_passage_ids": ["42"]},
        ]
        captured = {}
        def generate(**kwargs):
            captured["context"] = kwargs["context"]
            return model_answer(
                "Lăng gắn với vua Tự Đức.",
                follow_up_questions=[
                    "Tự Đức xây Khiêm Lăng trong hoàn cảnh nào?",
                    "Bi Đình trong Khiêm Lăng dùng để làm gì?",
                ],
            )
        with patch.object(chat_api, "generate_response", side_effect=generate):
            response = self.client.post("/api/chat", json={"message": "Khiêm Lăng của ai?"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("Bi Đình", captured["context"])
        self.assertIn("Tự Đức — Khiêm Lăng", captured["context"])
        self.assertIn("không cần cite", captured["context"])
        follow = response.json()["follow_up_questions"]
        self.assertGreaterEqual(len(follow), 2)
        self.assertTrue(any("Bi Đình" in item or "Hòa Khiêm" in item for item in follow))
        self.assertEqual(response.json()["sources"][0]["passage_id"], 42)

    def test_empty_model_follow_ups_are_filled_from_graph_topics(self):
        self.evidence.location_note = ""
        self.search.return_value.graph_context = [
            {"kind": "entity", "title": "Bi Đình", "source_passage_ids": ["42"]},
        ]
        with patch.object(chat_api, "generate_response", return_value=model_answer("Lăng gắn với vua Tự Đức.")):
            response = self.client.post("/api/chat", json={"message": "Khiêm Lăng của ai?"})
        self.assertEqual(response.status_code, 200, response.text)
        follow = response.json()["follow_up_questions"]
        self.assertGreaterEqual(len(follow), 2)
        self.assertLessEqual(len(follow), 3)
        self.assertTrue(any("Bi Đình" in item for item in follow))




    def test_accepts_bracketed_passage_label_in_source_ids(self):
        self.evidence.id = "PSG-a5249e9c6b65e5ae1b56174261805d80f38afc5829e376c25ffccb3ae152c7d3"
        self.evidence.to_source = lambda: {"passage_id": self.evidence.id}
        for cited_id in (
            f"[Passage {self.evidence.id}]",
            "a5249e9c6b65e5ae1b56174261805d80f38afc5829e376c25ffccb3ae152c7d3",
        ):
            with self.subTest(cited_id=cited_id):
                raw = model_answer(
                    "Lăng Tự Đức nằm ở thôn Thượng Ba, xã Thủy Xuân, thành phố Huế.",
                    source_ids=[cited_id],
                )
                with patch.object(chat_api, "generate_response", return_value=raw):
                    response = self.client.post("/api/chat", json={"message": "Lăng Tự Đức ở đâu?"})
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["answer_type"], "answered")
                self.assertEqual([s["passage_id"] for s in data["sources"]], [self.evidence.id])

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
                with patch.object(chat_api, "generate_response", side_effect=lambda **kw: model_answer(kw["context"])):
                    response = self.client.post("/api/chat", json={"message": question})
                self.assertEqual(response.status_code, 200)
                for fact in facts:
                    self.assertIn(fact, response.json()["answer"])

    def test_no_evidence_never_publishes_a_claim_even_if_model_says_answered(self):
        self.search.return_value.evidence = []
        with patch.object(chat_api, "generate_response", return_value=model_answer("Chùa ở Sao Hỏa.")) as generate:
            response = self.client.post("/api/chat", json={"message": "Chùa Sao Hỏa ở đâu?", "use_rag": False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["resolution_status"], "not_found")
        self.assertEqual(response.json()["sources"], [])
        self.assertNotIn("Chùa ở Sao Hỏa", response.json()["answer"])
        generate.assert_not_called()

    def test_uncited_answers_do_not_attach_unrelated_sources(self):
        with patch.object(chat_api, "generate_response", return_value=model_answer(
            "Mình chưa thể trả lời yêu cầu này.", source_ids=[])):
            response = self.client.post("/api/chat", json={"message": "Yêu cầu khác"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer_type"], "insufficient_evidence")
        self.assertEqual(response.json()["sources"], [])

    def test_blank_message_is_rejected(self):
        response = self.client.post("/api/chat", json={"message": "  "})
        self.assertEqual(response.status_code, 400)

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

    def test_retrieval_failures_return_specific_safe_errors(self):
        cases = [
            (Mock(side_effect=RuntimeError("private model path")), AsyncMock(),
             503, "EMBEDDING_FAILED", "Không thể tạo embedding cho câu hỏi."),
            (Mock(return_value=[[1.0]]), AsyncMock(side_effect=SearchError("private dependency URL")),
             503, "OPENSEARCH_FAILED", "Không thể truy vấn dữ liệu từ OpenSearch."),
            (Mock(return_value=[[1.0]]), AsyncMock(return_value=[{"private": "invalid passage"}]),
             500, "RETRIEVAL_INTERNAL_ERROR", "Đã xảy ra lỗi nội bộ khi truy xuất bằng chứng."),
        ]
        for embedder, search, status, code, message in cases:
            with self.subTest(code=code):
                repository = PassageRepository(SimpleNamespace(search=search), embedder=embedder)
                self.repository.return_value = repository
                with patch.object(chat_api, "generate_response", return_value=model_answer(
                    "Không thể xác nhận khi kho dữ liệu không khả dụng.", "insufficient_evidence", [])):
                    response = self.client.post("/api/chat", json={"message": "Chùa Thiên Mụ"})
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json(), {"detail": {"code": code, "message": message}})
                self.assertNotIn("private", response.text)

    def test_model_failure_returns_service_unavailable_without_leaking_details(self):
        with patch.object(chat_api, "generate_response", side_effect=RuntimeError("private dependency URL")):
            response = self.client.post("/api/chat", json={"message": "Chùa Thiên Mụ"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private", response.text)


class ChatGenerationContractTests(unittest.TestCase):
    """Exercise both entry points through generation, mocking only external IO."""

    def test_default_and_configured_deadlines_cover_standalone_and_tour_chat(self):
        wait_for = asyncio.wait_for
        for module_name in ("apps.backend.api.chat", "apps.backend.api.public.chat.router"):
            with patch.object(REGISTRY, "register"):
                api = importlib.import_module(module_name)
            for area in (None, "khiem-lang"):
                for budget, expected_status in (("", 200), ("0.01", 504), ("0.3", 200)):
                    with self.subTest(api=module_name, area=area, budget=budget):
                        evidence = SimpleNamespace(
                            id="42", text="Khiêm Lăng gắn với vua Tự Đức.", active_area_id=area,
                            to_source=lambda: {"passage_id": "42", "active_area_id": area},
                        )
                        repository = SimpleNamespace(search_evidence=AsyncMock(return_value=SimpleNamespace(
                            query=SimpleNamespace(ambiguous=False, corrections=[], intent=frozenset()),
                            evidence=[evidence], graph_context=[],
                        )))
                        app = FastAPI()
                        app.include_router(api.router, prefix="/api")
                        app.dependency_overrides[api.get_repository] = lambda: repository

                        def generate(**kwargs):
                            time.sleep(.06)
                            return model_answer("Khiêm Lăng gắn với vua Tự Đức.")

                        async def deadline(coro, timeout):
                            # Scale the default seconds to milliseconds: a 60-second
                            # answer must outlive the old 30s limit, not the new 120s.
                            return await wait_for(coro, timeout=timeout * .001 if not budget else timeout)

                        with (
                            patch.dict(os.environ, {"CHAT_TIMEOUT_SECONDS": budget}),
                            patch.object(api, "generate_response", side_effect=generate),
                            patch.object(api, "get_generation_details", return_value=SimpleNamespace(
                                truncated=False, model="test", token_usage=10,
                            )),
                            patch.object(api.asyncio, "wait_for", side_effect=deadline),
                            TestClient(app) as client,
                        ):
                            response = client.post("/api/chat", json={
                                "message": "Khiêm Lăng gắn với ai?", "active_area_id": area,
                            })
                        self.assertEqual(response.status_code, expected_status, response.text)
                        if expected_status == 200:
                            self.assertEqual(response.json()["sources"][0]["passage_id"], "42")
                        else:
                            self.assertIn("0.01", response.json()["detail"])
                            self.assertNotIn("Khiêm Lăng", response.text)

    @patch.dict("os.environ", {"INFERENCE_BACKEND": "llama_server"})
    def test_single_generation_preserves_question_and_controls_citations(self):
        cases = [
            ("hi", "conversation", [], False),
            ("Bạn là ai?", "conversation", ["42"], False),
            ("Hi, Thiên Mụ xây năm nào?", "answered", ["42", "91"], True),
            ("Thiên Mụ xây năm nào?", "insufficient_evidence", [], False),
            ("Viết giúp code game", "insufficient_evidence", [], False),
        ]
        for module_name in ("apps.backend.api.chat", "apps.backend.api.public.chat.router"):
            with patch.object(REGISTRY, "register"):
                api = importlib.import_module(module_name)
            for question, kind, ids, calls_model in cases:
                with self.subTest(api=module_name, question=question):
                    evidence = [SimpleNamespace(
                        id=id_, text=f"Tài liệu {id_}",
                        to_source=lambda id_=id_: {"passage_id": id_},
                    ) for id_ in ids]
                    repository = SimpleNamespace(search_evidence=AsyncMock(return_value=SimpleNamespace(
                        query=SimpleNamespace(ambiguous=False, corrections=[], intent=frozenset()),
                        evidence=evidence, graph_context=[],
                    )))
                    app = FastAPI()
                    app.include_router(api.router, prefix="/api")
                    app.dependency_overrides[api.get_repository] = lambda: repository
                    cited = ["91"] if kind == "answered" else []
                    upstream = Mock()
                    upstream.json.return_value = {
                        "choices": [{"message": {"content": model_answer("Lời đáp", source_ids=cited)},
                                     "finish_reason": "stop"}],
                        "model": "qwen3-4b", "usage": {"total_tokens": 37},
                    }
                    with TestClient(app) as client, patched_llama_http(return_value=upstream) as post:
                        response = client.post("/api/chat", json={"message": question})
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()["answer_type"], kind)
                    self.assertEqual(response.json()["sources"], [{"passage_id": id_} for id_ in cited])
                    if not calls_model:
                        post.assert_not_called()
                        continue
                    self.assertEqual(response.json()["answer"], "Lời đáp")
                    post.assert_called_once()
                    payload = post.call_args.kwargs["json"]
                    self.assertIn(f"Câu hỏi: {question}", payload["messages"][-1]["content"])
                    self.assertEqual(payload["response_format"]["type"], "json_object")
                    self.assertEqual(set(payload["response_format"]["schema"]["required"]),
                                     {"answer_type", "answer", "source_ids"})
                    self.assertEqual(payload["chat_template_kwargs"], {"enable_thinking": False})
                    self.assertIn("HeritageGraph", payload["messages"][0]["content"])

    def test_migrated_api_preserves_errors_and_allows_conversation_during_outage(self):
        with patch.object(REGISTRY, "register"):
            api = importlib.import_module("apps.backend.api.public.chat.router")
        cases = [
            (api.EmbeddingError("private"), 503, "EMBEDDING_FAILED"),
            (api.SearchError("private"), 503, "OPENSEARCH_FAILED"),
            (RuntimeError("private"), 500, "RETRIEVAL_INTERNAL_ERROR"),
            (None, 200, None),
        ]
        for error, status, code in cases:
            with self.subTest(error=error, status=status):
                repository = SimpleNamespace(search_evidence=AsyncMock(
                    side_effect=error, return_value=SimpleNamespace(
                        query=SimpleNamespace(ambiguous=False, corrections=[], intent=frozenset()),
                        evidence=[], graph_context=[],
                    ),
                ))
                app = FastAPI()
                app.include_router(api.router, prefix="/api")
                app.dependency_overrides[api.get_repository] = lambda: repository
                with TestClient(app) as client, patched_llama_http() as post:
                    response = client.post("/api/chat", json={"message": "Nội dung người dùng"})
                self.assertEqual(response.status_code, status)
                self.assertNotIn("private", response.text)
                post.assert_not_called()
                if code:
                    self.assertEqual(response.json()["detail"]["code"], code)
                else:
                    self.assertEqual(response.json()["sources"], [])
                    self.assertEqual(response.json()["answer_type"], "insufficient_evidence")

    def test_truncated_json_is_rejected_without_retry(self):
        repository = SimpleNamespace(search_evidence=AsyncMock(return_value=SimpleNamespace(
            query=SimpleNamespace(ambiguous=False),
            evidence=[SimpleNamespace(id="42", text="Nguồn", to_source=lambda: {"passage_id": "42"})],
            graph_context=[],
        )))
        app = FastAPI()
        app.include_router(chat_api.router, prefix="/api")
        app.dependency_overrides[chat_api.get_repository] = lambda: repository
        upstream = Mock()
        upstream.json.return_value = {"choices": [{
            "message": {"content": model_answer("Câu trả lời", source_ids=["42"])},
            "finish_reason": "length",
        }]}
        with TestClient(app) as client, patched_llama_http(return_value=upstream) as post:
            response = client.post("/api/chat", json={"message": "Thiên Mụ ở đâu?"})
        self.assertEqual(response.status_code, 503)
        post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
