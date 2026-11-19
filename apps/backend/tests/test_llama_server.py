import asyncio
import json
import threading
import time
import unittest
from unittest.mock import Mock, patch

import httpx

from apps.backend.core import llm


class LlamaServerTests(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_llama_server_is_the_portable_default_backend(self) -> None:
        llm.get_model.cache_clear()

        self.assertEqual(llm.get_model(), (None, None, "llama_server"))

    @patch.dict(
        "os.environ",
        {
            "LLAMA_SERVER_URL": "http://llm:8080",
            "LLAMA_SERVER_TIMEOUT": "45",
        },
        clear=False,
    )
    def test_generate_posts_openai_compatible_chat_request(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": "Câu trả lời"}}],
            "model": "qwen-local",
            "usage": {"total_tokens": 42},
        }

        with patch("apps.backend.core.llm.httpx.post", return_value=response) as post:
            result = llm._llama_server_generate(
                [{"role": "user", "content": "Xin chào"}],
                max_tokens=123,
            )

        self.assertEqual(result, "Câu trả lời")
        self.assertEqual(llm.generation_details.get().model, "qwen-local")
        self.assertEqual(llm.generation_details.get().token_usage, 42)
        post.assert_called_once_with(
            "http://llm:8080/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Xin chào"}],
                "temperature": 0.0,
                "max_tokens": 123,
            },
            timeout=45.0,
        )

    def test_embedded_generation_captures_model_and_usage(self) -> None:
        model = Mock(model_path="qwen-local")
        model.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "Câu trả lời"}}],
            "usage": {"total_tokens": 11},
        }

        self.assertEqual(llm._llama_cpp_generate(model, [], 10), "Câu trả lời")
        self.assertEqual(llm.get_generation_details().model, "qwen-local")
        self.assertEqual(llm.get_generation_details().token_usage, 11)

    @patch.dict("os.environ", {"INFERENCE_BACKEND": "llama_server"}, clear=False)
    def test_generate_response_uses_llama_server_backend(self) -> None:
        llm.get_model.cache_clear()
        with patch(
            "apps.backend.core.llm._llama_server_generate",
            return_value="portable",
        ) as generate:
            result = llm.generate_response("Câu hỏi", "Nguồn", max_tokens=99)

        self.assertEqual(result, "portable")
        generate.assert_called_once_with(
            llm.chat_messages("Nguồn", "Câu hỏi"),
            max_tokens=99,
        )

    def test_structured_conversation_also_works_with_embedded_backend(self) -> None:
        raw = json.dumps({"answer_type": "conversation", "answer": "Chào bạn", "source_ids": []})
        model = Mock(model_path="qwen3-4b")
        model.create_chat_completion.return_value = {
            "choices": [{"message": {"content": raw}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 19},
        }
        with patch.object(llm, "get_model", return_value=(model, None, "llama_cpp")):
            answer = llm.generate_response("Thiên Mụ ở đâu?", conversation=True, retrieval_status="not_found")
        self.assertEqual(answer, raw)
        model.create_chat_completion.assert_called_once()
        options = model.create_chat_completion.call_args.kwargs
        self.assertEqual(options["response_format"]["type"], "json_object")
        self.assertEqual(set(options["response_format"]["schema"]["required"]), {"answer_type", "answer", "source_ids"})
        self.assertIn("Câu hỏi: Thiên Mụ ở đâu?", options["messages"][-1]["content"])
        self.assertEqual(llm.get_generation_details().token_usage, 19)

    def test_conversation_messages_exclude_history(self) -> None:
        from apps.backend.ai.answering.conversation import conversation_messages

        messages = conversation_messages("Nguồn mới", "Còn kiến trúc?")

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[-1]["role"], "user")
        self.assertIn("Nguồn: Nguồn mới", messages[-1]["content"])
        self.assertIn("Câu hỏi: Còn kiến trúc?", messages[-1]["content"])
        self.assertNotIn("Lăng Tự Đức", messages[-1]["content"])

    def test_abort_scope_closes_in_flight_llama_http_client(self) -> None:
        started = threading.Event()

        def blocking_post(self, url, **kwargs):
            started.set()
            deadline = time.monotonic() + 2
            while not self.is_closed and time.monotonic() < deadline:
                time.sleep(0.01)
            if not self.is_closed:
                raise AssertionError("llama client was not closed")
            raise httpx.TransportError("closed")

        async def run() -> None:
            async with llm.llama_abort_scope() as abort:
                worker = asyncio.create_task(asyncio.to_thread(
                    llm._llama_server_generate,
                    [{"role": "user", "content": "Xin chào"}],
                    8,
                ))
                await asyncio.to_thread(started.wait, 2)
                abort.abort()
                with self.assertRaises(httpx.RequestError):
                    await worker

        with patch.object(httpx.Client, "post", blocking_post):
            asyncio.run(run())




if __name__ == "__main__":
    unittest.main()
