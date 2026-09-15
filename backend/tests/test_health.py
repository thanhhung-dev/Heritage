import unittest
from unittest.mock import Mock, patch

import httpx
from fastapi.testclient import TestClient

from backend.app import app


class HealthEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    @patch.dict(
        "os.environ",
        {
            "INFERENCE_BACKEND": "llama_server",
            "LLAMA_SERVER_URL": "http://llm:8080",
        },
        clear=False,
    )
    @patch("backend.api.health.httpx.get")
    def test_health_is_ready_when_llama_server_responds(self, get: Mock) -> None:
        get.return_value.raise_for_status.return_value = None

        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "inference_backend": "llama_server",
                "model_ready": True,
                "corpus_ready": True,
            },
        )
        get.assert_called_once_with("http://llm:8080/health", timeout=2.0)

    @patch.dict(
        "os.environ",
        {
            "INFERENCE_BACKEND": "llama_server",
            "LLAMA_SERVER_URL": "http://llm:8080",
        },
        clear=False,
    )
    @patch(
        "backend.api.health.httpx.get",
        side_effect=httpx.ConnectError("not ready"),
    )
    def test_health_returns_503_until_llama_server_is_ready(self, _: Mock) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["model_ready"], False)

    @patch.dict(
        "os.environ",
        {
            "INFERENCE_BACKEND": "transformers_peft",
            "PEFT_ADAPTER_PATH": "models/peft-adapter/checkpoint-125",
        },
        clear=False,
    )
    def test_health_is_ready_when_peft_adapter_exists(self) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["inference_backend"], "transformers_peft")
        self.assertTrue(response.json()["model_ready"])


if __name__ == "__main__":
    unittest.main()
