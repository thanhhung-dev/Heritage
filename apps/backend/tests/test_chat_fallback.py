"""Development fallback contracts, HTTP failures and actual conversation writes."""
import asyncio
import json
import os
import time
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from apps.backend.models.chat import ChatMessage
from apps.backend.services import chat_fallback
from apps.backend.tests import test_chat_conversation as persistence_tests


class DevelopmentAnswerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"APP_ENVIRONMENT": "local", "GOOGLE_API_KEY": ""}))

    async def test_only_local_environment_enables_fallback(self):
        for environment in ("production", "staging", "test", "unknown"):
            with self.subTest(environment=environment), patch.dict(os.environ, {"APP_ENVIRONMENT": environment}):
                self.assertFalse(chat_fallback.development_fallback_enabled())
                with self.assertRaises(RuntimeError):
                    await chat_fallback.development_answer("Question")

    async def test_no_key_returns_labelled_fixture_with_no_fabricated_source_url(self):
        result = await chat_fallback.development_answer("Chùa Thiên Mụ xây năm nào?")
        self.assertEqual(result.answer_type, "development_mock")
        self.assertIn("MÔ PHỎNG DEVELOPMENT", result.answer)
        self.assertEqual(result.sources, [chat_fallback.DEMO_SOURCE])
        self.assertIsNone(result.sources[0]["url"])
        self.assertIsNone(result.sources[0]["score"])

    async def test_gemini_uses_retrieved_evidence_and_keeps_its_original_sources(self):
        sources = [{"passage_id": "42", "doc": "Original source", "url": "https://example.org/source"}]
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}), patch.object(
            chat_fallback, "_gemini_answer", new=AsyncMock(return_value="Grounded answer"),
        ) as generate:
            result = await chat_fallback.development_answer("Question", context="Evidence", sources=sources)
        generate.assert_awaited_once_with("Question", "Evidence", "test-key")
        self.assertEqual(result.answer, "Grounded answer")
        self.assertEqual(result.sources, sources)
        self.assertEqual(result.resolution_status, "gemini_fallback")
        self.assertEqual(result.answer_type, "answered")

    async def test_gemini_without_retrieval_remains_labelled_demo(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}), patch.object(
            chat_fallback, "_gemini_answer", new=AsyncMock(return_value="Demo response"),
        ) as generate:
            result = await chat_fallback.development_answer("Question")
        self.assertEqual(generate.await_args.args[1], chat_fallback.DEMO_CONTEXT)
        self.assertEqual(result.answer_type, "development_mock")
        self.assertIn("MÔ PHỎNG DEVELOPMENT", result.answer)

    async def test_gemini_errors_or_malformed_responses_fall_back_without_leaking_details(self):
        errors = [
            httpx.ConnectError("private key or upstream configuration"),
            httpx.HTTPStatusError("private upstream body", request=httpx.Request("POST", "https://example.org"), response=httpx.Response(429)),
            ValueError("invalid JSON"), KeyError("candidates"), IndexError(), TypeError(),
        ]
        for error in errors:
            with self.subTest(error=type(error).__name__), patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}), patch.object(
                chat_fallback, "_gemini_answer", new=AsyncMock(side_effect=error),
            ):
                result = await chat_fallback.development_answer("Question")
            self.assertEqual(result.answer_type, "development_mock")
            self.assertNotIn("private", result.answer)
            self.assertNotIn("test-key", result.answer)

    async def test_gemini_timeout_is_bounded_and_returns_mock(self):
        async def slow(*_):
            await asyncio.sleep(1)
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}), patch.object(
            chat_fallback, "_gemini_answer", new=slow,
        ), patch.object(chat_fallback, "GEMINI_TIMEOUT_SECONDS", 0.01):
            result = await chat_fallback.development_answer("Question")
        self.assertEqual(result.answer_type, "development_mock")

    async def test_gemini_http_contract_uses_key_header_and_rejects_incomplete_output(self):
        real_client = httpx.AsyncClient
        finish_reason = "STOP"
        history = []

        def handle(request):
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.url.host, "generativelanguage.googleapis.com")
            self.assertEqual(request.headers["x-goog-api-key"], "test-key")
            self.assertNotIn("test-key", str(request.url))
            self.assertTrue(request.url.path.endswith("/models/test-model:generateContent"))
            body = json.loads(request.content)
            self.assertIn("NGUỒN:\nEvidence", body["contents"][-1]["parts"][0]["text"])
            self.assertEqual([item["role"] for item in body["contents"]],
                             ["user", "model", "user"] if history else ["user"])
            self.assertEqual(body["generationConfig"]["temperature"], 0)
            return httpx.Response(200, json={"candidates": [{
                "finishReason": finish_reason,
                "content": {"parts": [{"thought": True, "text": "hidden"}, {"text": "Answer"}]},
            }]})

        with patch.dict(os.environ, {"GEMINI_MODEL": "test-model"}), patch.object(
            chat_fallback.httpx, "AsyncClient",
            side_effect=lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
        ):
            self.assertEqual(await chat_fallback._gemini_answer("Question", "Evidence", "test-key"), "Answer")
            history = [{"role": "user", "content": "Previous question"}, {"role": "assistant", "content": "Previous answer"}]
            self.assertEqual(await chat_fallback._gemini_answer("Question", "Evidence", "test-key", history=history), "Answer")
            finish_reason = "MAX_TOKENS"
            with self.assertRaises(ValueError):
                await chat_fallback._gemini_answer("Question", "Evidence", "test-key", history=history)


class LocalFallbackPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = persistence_tests.ChatConversationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.enterContext(patch.dict(os.environ, {"APP_ENVIRONMENT": "local", "GOOGLE_API_KEY": "", "CHAT_DEVELOPMENT_FALLBACK": "true"}))

    def test_local_missing_model_persists_labelled_mock_with_original_sources(self):
        self.fixture.generate.side_effect = FileNotFoundError("model unavailable")
        reply = self.fixture.create_conversation()
        self.assertEqual(reply["answer_type"], "development_mock")
        self.assertIn("MÔ PHỎNG DEVELOPMENT", reply["answer"])
        self.assertEqual(reply["citations"][0]["source_title"], self.fixture.source["doc"])
        self.assertEqual(self.fixture.counts(), (1, 2, 1))

    def test_local_scoped_outage_abstains_without_gemini_or_foreign_sample_sources(self):
        self.fixture.generate.side_effect = FileNotFoundError("model unavailable")
        with patch.object(chat_fallback, "development_answer", new=AsyncMock()) as generic_fallback:
            reply = self.fixture.create_conversation(active_area_id="chua-thien-mu")
        self.assertEqual(reply["active_area_id"], "chua-thien-mu")
        self.assertTrue(reply["abstained"])
        self.assertEqual(reply["abstention_reason"], "service_unavailable")
        self.assertEqual(reply["sources"], [])
        self.assertEqual(reply["citations"], [])
        generic_fallback.assert_not_called()

    def test_local_short_inference_timeout_never_appends_a_late_answer(self):
        def slow(**_):
            time.sleep(.08)
            return "late answer"
        self.fixture.generate.side_effect = slow
        with patch.object(chat_fallback, "LOCAL_INFERENCE_TIMEOUT_SECONDS", .01):
            reply = self.fixture.create_conversation()
        time.sleep(.1)
        self.assertEqual(reply["answer_type"], "development_mock")
        self.assertEqual(self.fixture.counts(), (1, 2, 1))

    def test_development_fallback_can_be_disabled_and_is_never_used_in_production(self):
        self.fixture.generate.side_effect = FileNotFoundError("model unavailable")
        for environment, flag in (("production", "true"), ("local", "false")):
            with patch.dict(os.environ, {"APP_ENVIRONMENT": environment, "CHAT_DEVELOPMENT_FALLBACK": flag}):
                response = self.fixture.client.post("/api/chat/message", headers=self.fixture.headers(), json={"message": "test"})
                self.assertEqual(response.status_code, 500)
        self.assertEqual(self.fixture.counts(), (0, 0, 0))


