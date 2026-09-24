import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from apps.backend.app import app


class HealthEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    @patch("apps.backend.api.health._corpus_is_ready")
    @patch("apps.backend.api.health._model_is_ready", new_callable=AsyncMock)
    @patch("apps.backend.api.health._database_is_ready", new_callable=AsyncMock)
    def test_live_does_not_check_dependencies(
        self,
        database_ready: AsyncMock,
        model_ready: AsyncMock,
        corpus_ready: Mock,
    ) -> None:
        response = self.client.get("/api/live")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "live"})
        database_ready.assert_not_awaited()
        model_ready.assert_not_awaited()
        corpus_ready.assert_not_called()

    @patch.dict("os.environ", {"INFERENCE_BACKEND": "llama_server"}, clear=False)
    @patch("apps.backend.api.health._corpus_is_ready", return_value=True)
    @patch(
        "apps.backend.api.health._model_is_ready",
        new_callable=AsyncMock,
        return_value=True,
    )
    @patch(
        "apps.backend.api.health._database_is_ready",
        new_callable=AsyncMock,
        return_value=True,
    )
    def test_ready_returns_200_when_all_dependencies_are_ready(
        self, database_ready: AsyncMock, model_ready: AsyncMock, _: Mock
    ) -> None:
        response = self.client.get("/api/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ready",
                "inference_backend": "llama_server",
                "database_ready": True,
                "model_ready": True,
                "corpus_ready": True,
            },
        )
        database_ready.assert_awaited_once_with()
        model_ready.assert_awaited_once_with("llama_server")

    @patch("apps.backend.api.health._corpus_is_ready", return_value=True)
    @patch(
        "apps.backend.api.health._model_is_ready",
        new_callable=AsyncMock,
        return_value=True,
    )
    @patch(
        "apps.backend.api.health._database_is_ready",
        new_callable=AsyncMock,
        return_value=False,
    )
    def test_ready_returns_503_when_database_is_unavailable(
        self, _: AsyncMock, __: AsyncMock, ___: Mock
    ) -> None:
        response = self.client.get("/api/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["status"], "not_ready")
        self.assertFalse(response.json()["detail"]["database_ready"])

    @patch("apps.backend.api.health._corpus_is_ready", return_value=True)
    @patch(
        "apps.backend.api.health._model_is_ready",
        new_callable=AsyncMock,
        return_value=False,
    )
    @patch(
        "apps.backend.api.health._database_is_ready",
        new_callable=AsyncMock,
        return_value=True,
    )
    def test_ready_returns_503_when_model_is_unavailable(
        self, _: AsyncMock, __: AsyncMock, ___: Mock
    ) -> None:
        response = self.client.get("/api/ready")

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["detail"]["model_ready"])

    @patch("apps.backend.api.health._corpus_is_ready", return_value=True)
    @patch(
        "apps.backend.api.health._model_is_ready",
        new_callable=AsyncMock,
        return_value=True,
    )
    @patch(
        "apps.backend.api.health._database_is_ready",
        new_callable=AsyncMock,
        return_value=True,
    )
    def test_health_remains_a_readiness_alias(
        self, _: AsyncMock, __: AsyncMock, ___: Mock
    ) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")

    @patch("apps.backend.api.health._corpus_is_ready", return_value=True)
    @patch(
        "apps.backend.api.health._model_is_ready",
        new_callable=AsyncMock,
        return_value=True,
    )
    @patch(
        "apps.backend.api.health._database_is_ready",
        new_callable=AsyncMock,
        return_value=False,
    )
    def test_readiness_response_does_not_expose_connection_secrets(
        self, _: AsyncMock, __: AsyncMock, ___: Mock
    ) -> None:
        secret = "postgresql+psycopg://user:super-secret@db:5432/app"
        with patch.dict("os.environ", {"DATABASE_URL": secret}, clear=False):
            response = self.client.get("/api/ready")

        self.assertNotIn(secret, response.text)
        self.assertNotIn("super-secret", response.text)


if __name__ == "__main__":
    unittest.main()
