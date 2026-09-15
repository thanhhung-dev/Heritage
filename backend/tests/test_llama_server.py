import unittest
from unittest.mock import Mock, patch

from backend.core import llm


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
            "choices": [{"message": {"content": "Câu trả lời"}}]
        }

        with patch("backend.core.llm.httpx.post", return_value=response) as post:
            result = llm._llama_server_generate(
                [{"role": "user", "content": "Xin chào"}],
                max_tokens=123,
            )

        self.assertEqual(result, "Câu trả lời")
        post.assert_called_once_with(
            "http://llm:8080/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Xin chào"}],
                "temperature": 0.0,
                "max_tokens": 123,
            },
            timeout=45.0,
        )

    @patch.dict("os.environ", {"INFERENCE_BACKEND": "llama_server"}, clear=False)
    def test_generate_response_uses_llama_server_backend(self) -> None:
        llm.get_model.cache_clear()
        with patch(
            "backend.core.llm._llama_server_generate",
            return_value="portable",
        ) as generate:
            result = llm.generate_response("Câu hỏi", "Nguồn", max_tokens=99)

        self.assertEqual(result, "portable")
        generate.assert_called_once_with(
            llm.chat_messages("Nguồn", "Câu hỏi"),
            max_tokens=99,
        )

    @patch.dict(
        "os.environ",
        {
            "INFERENCE_BACKEND": "transformers_peft",
            "HF_MODEL_ID": "Qwen/Qwen3-4B",
            "PEFT_ADAPTER_PATH": "models/peft-adapter/checkpoint-125",
        },
        clear=False,
    )
    def test_transformers_peft_backend_loads_configured_adapter(self) -> None:
        llm.get_model.cache_clear()

        with patch(
            "backend.core.llm._load_transformers_peft",
            return_value=("model", "tokenizer"),
            create=True,
        ) as load:
            result = llm.get_model()

        self.assertEqual(result, ("model", "tokenizer", "transformers_peft"))
        load.assert_called_once_with(
            "Qwen/Qwen3-4B",
            "models/peft-adapter/checkpoint-125",
        )

    def test_generate_response_uses_transformers_peft_backend(self) -> None:
        messages = llm.chat_messages("Nguồn", "Câu hỏi")
        with (
            patch.object(
                llm,
                "get_model",
                return_value=("model", "tokenizer", "transformers_peft"),
            ),
            patch(
                "backend.core.llm._transformers_generate",
                return_value="adapter",
                create=True,
            ) as generate,
        ):
            result = llm.generate_response("Câu hỏi", "Nguồn", max_tokens=99)

        self.assertEqual(result, "adapter")
        generate.assert_called_once_with(
            "model",
            "tokenizer",
            messages,
            max_tokens=99,
        )

    def test_chat_messages_include_recent_conversation_before_current_source(self) -> None:
        history = [
            {"role": "user", "content": "Lăng Tự Đức ở đâu?"},
            {"role": "assistant", "content": "Lăng Tự Đức nằm ở Huế."},
        ]

        messages = llm.chat_messages("Nguồn mới", "Còn kiến trúc?", history=history)

        self.assertEqual(messages[1:3], history)
        self.assertEqual(messages[-1]["role"], "user")
        self.assertIn("Nguồn: Nguồn mới", messages[-1]["content"])


if __name__ == "__main__":
    unittest.main()
