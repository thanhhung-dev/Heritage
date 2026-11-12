import asyncio
import importlib
import json
import os
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from apps.backend.api import chat as chat_api
from apps.backend.core.search import SearchError
from apps.backend.services.passages import PassageRepository


def model_answer(text, answer_type="answered", source_ids=None):
    return json.dumps({"answer": text, "answer_type": answer_type,
                       "source_ids": source_ids if source_ids is not None else ["42"]})


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
        for question in ("hi", "Bạn là ai?", "Cảm ơn bạn nhé", "Bạn có thể giúp gì?"):
            for has_evidence in (True, False):
                with self.subTest(question=question, has_evidence=has_evidence):
                    self.search.return_value.evidence = [self.evidence] if has_evidence else []
                    reply = "Mình là trợ lý AI HeritageGraph."
                    with (
                        patch.object(chat_api, "generate_response", return_value=model_answer(
                            reply, "conversation", [])) as generate,
                        patch.object(chat_api, "observe_grounded_qa") as observe,
                    ):
                        response = self.client.post("/api/chat", json={"message": question})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["answer"], reply)
                    self.assertEqual(response.json()["answer_type"], "conversation")
                    self.assertEqual(response.json()["sources"], [])
                    generate.assert_called_once()
                    self.assertEqual(generate.call_args.kwargs["question"], question)
                    self.assertFalse(observe.call_args.kwargs["grounded"])
                    self.assertEqual(observe.call_args.kwargs["evidence_ids"], [])

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
        cases = ["unstructured answer", "{}", model_answer("Bịa", source_ids=["999"]),
                 model_answer("Bịa", source_ids=[]),
                 model_answer("Bịa", "conversation", ["42"]),
                 model_answer("  ", "conversation", [])]
        for raw in cases:
            with self.subTest(raw=raw), patch.object(chat_api, "generate_response", return_value=raw):
                response = self.client.post("/api/chat", json={"message": "Thiên Mụ ở đâu?"})
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("Bịa", response.text)

    def test_conversation_survives_retrieval_failure(self):
        self.search.side_effect = SearchError("private dependency URL")
        with patch.object(chat_api, "generate_response", return_value=model_answer(
            "Chào bạn! Mình là trợ lý AI HeritageGraph.", "conversation", [])) as generate:
            response = self.client.post("/api/chat", json={"message": "Chào bạn"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer_type"], "conversation")
        self.assertEqual(response.json()["sources"], [])
        self.assertEqual(generate.call_args.kwargs["retrieval_status"], "unavailable")
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
        for raw in (model_answer("Chùa ở Sao Hỏa."),
                    model_answer("Mình chưa có bằng chứng về địa điểm này.", "insufficient_evidence", [])):
            with self.subTest(raw=raw), patch.object(chat_api, "generate_response", return_value=raw):
                response = self.client.post("/api/chat", json={"message": "Chùa Sao Hỏa ở đâu?", "use_rag": False})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["resolution_status"], "not_found")
                self.assertEqual(response.json()["sources"], [])
                self.assertNotIn("Chùa ở Sao Hỏa", response.json()["answer"])

    def test_insufficient_evidence_and_out_of_scope_do_not_attach_unrelated_sources(self):
        for kind in ("insufficient_evidence", "out_of_scope"):
            with self.subTest(kind=kind), patch.object(chat_api, "generate_response", return_value=model_answer(
                "Mình chưa thể trả lời yêu cầu này.", kind, [])):
                response = self.client.post("/api/chat", json={"message": "Yêu cầu khác"})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["answer_type"], kind)
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
            ("hi", "conversation", [], "not_found"),
            ("Bạn là ai?", "conversation", ["42"], "available"),
            ("Hi, Thiên Mụ xây năm nào?", "answered", ["42", "91"], "available"),
            ("Thiên Mụ xây năm nào?", "insufficient_evidence", [], "not_found"),
            ("Viết giúp code game", "out_of_scope", [], "not_found"),
        ]
        for module_name in ("apps.backend.api.chat", "apps.backend.api.public.chat.router"):
            # Legacy and migrated entry points own identical metric names and
            # normally run separately. Isolate metric registration for this test.
            with patch.object(REGISTRY, "register"):
                api = importlib.import_module(module_name)
            for question, kind, ids, status in cases:
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
                        "choices": [{"message": {"content": model_answer("Lời đáp", kind, cited)},
                                     "finish_reason": "stop"}],
                        "model": "qwen3-4b", "usage": {"total_tokens": 37},
                    }
                    with TestClient(app) as client, patch("httpx.post", return_value=upstream) as post:
                        response = client.post("/api/chat", json={"message": question})
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()["answer"], "Lời đáp")
                    self.assertEqual(response.json()["answer_type"], kind)
                    self.assertEqual(response.json()["sources"], [{"passage_id": id_} for id_ in cited])
                    post.assert_called_once()
                    payload = post.call_args.kwargs["json"]
                    data = json.loads(payload["messages"][-1]["content"])
                    self.assertEqual(data["message"], question)
                    self.assertEqual(data["retrieval_status"], status)
                    self.assertEqual(payload["response_format"]["type"], "json_object")
                    self.assertEqual(set(payload["response_format"]["schema"]["required"]),
                                     {"answer", "answer_type", "source_ids"})
                    self.assertEqual(payload["chat_template_kwargs"], {"enable_thinking": False})
                    self.assertIn("HeritageGraph", payload["messages"][0]["content"])

    def test_migrated_api_preserves_errors_and_allows_conversation_during_outage(self):
        with patch.object(REGISTRY, "register"):
            api = importlib.import_module("apps.backend.api.public.chat.router")
        cases = [
            (api.EmbeddingError("private"), "insufficient_evidence", 503, "EMBEDDING_FAILED"),
            (api.SearchError("private"), "insufficient_evidence", 503, "OPENSEARCH_FAILED"),
            (RuntimeError("private"), "insufficient_evidence", 500, "RETRIEVAL_INTERNAL_ERROR"),
            (api.SearchError("private"), "conversation", 200, None),
            (None, "answered", 200, None),  # Missing sources cannot authorize facts.
        ]
        for error, kind, status, code in cases:
            with self.subTest(error=error, kind=kind):
                repository = SimpleNamespace(search_evidence=AsyncMock(
                    side_effect=error, return_value=SimpleNamespace(
                        query=SimpleNamespace(ambiguous=False, corrections=[], intent=frozenset()),
                        evidence=[], graph_context=[],
                    ),
                ))
                app = FastAPI()
                app.include_router(api.router, prefix="/api")
                app.dependency_overrides[api.get_repository] = lambda: repository
                upstream = Mock()
                upstream.json.return_value = {"choices": [{"message": {"content": model_answer(
                    "Lời đáp", kind, ["42"] if kind == "answered" else [],
                )}, "finish_reason": "stop"}]}
                with TestClient(app) as client, patch("httpx.post", return_value=upstream) as post:
                    response = client.post("/api/chat", json={"message": "Nội dung người dùng"})
                self.assertEqual(response.status_code, status)
                self.assertNotIn("private", response.text)
                post.assert_called_once()
                if code:
                    self.assertEqual(response.json()["detail"]["code"], code)
                else:
                    self.assertEqual(response.json()["sources"], [])
                    self.assertEqual(response.json()["answer_type"],
                                     "insufficient_evidence" if kind == "answered" else kind)

    def test_truncated_json_is_rejected_without_retry(self):
        repository = SimpleNamespace(search_evidence=AsyncMock(return_value=SimpleNamespace(
            query=SimpleNamespace(ambiguous=False), evidence=[], graph_context=[],
        )))
        app = FastAPI()
        app.include_router(chat_api.router, prefix="/api")
        app.dependency_overrides[chat_api.get_repository] = lambda: repository
        upstream = Mock()
        upstream.json.return_value = {"choices": [{
            "message": {"content": model_answer("Chào bạn", "conversation", [])},
            "finish_reason": "length",
        }]}
        with TestClient(app) as client, patch("httpx.post", return_value=upstream) as post:
            response = client.post("/api/chat", json={"message": "hi"})
        self.assertEqual(response.status_code, 503)
        post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
