import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from apps.backend.app import app
from apps.backend.core.config import ConfigurationError, validate_startup_config


VALID_ENV = {
    "DATABASE_URL": (
        "postgresql+psycopg://heritagegraph:test-password@localhost:5433/heritagegraph"
    ),
    "INFERENCE_BACKEND": "llama_server",
    "LLAMA_SERVER_URL": "http://localhost:8080",
    "LLAMA_SERVER_TIMEOUT": "30",
}


class StartupConfigTests(unittest.TestCase):
    def setUp(self):
        # Model IO is external; lifecycle tests must not download BGE-M3.
        self.embedding = self.enterContext(patch("apps.backend.core.embedding.embed_texts"))

    def test_chat_only_configuration_does_not_require_postgres(self) -> None:
        settings = validate_startup_config({})
        self.assertEqual(settings.database_url, '')

    def test_chat_timeout_defaults_and_configuration_for_both_config_paths(self):
        from apps.backend.common import config as common_config
        from apps.backend.core import config as core_config

        for config in (core_config, common_config):
            with self.subTest(config=config.__name__):
                self.assertEqual(config.validate_startup_config({}).chat_timeout_seconds, 120)
                self.assertEqual(config.validate_startup_config({
                    "CHAT_TIMEOUT_SECONDS": "45.5",
                }).chat_timeout_seconds, 45.5)
                for invalid in ("0", "-1", "bad", "nan", "inf"):
                    with self.subTest(value=invalid), self.assertRaises(config.ConfigurationError) as error:
                        config.validate_startup_config({"CHAT_TIMEOUT_SECONDS": invalid})
                    self.assertIn("CHAT_TIMEOUT_SECONDS", str(error.exception))

    def test_embedding_is_ready_before_lifespan_accepts_requests(self):
        ready = []
        self.embedding.side_effect = lambda texts: ready.extend(texts)
        with patch.dict(os.environ, {}, clear=True), TestClient(app) as client:
            self.assertTrue(ready, "Startup must initialize and encode with the query embedding model")
            self.assertEqual(client.get('/').status_code, 200)

    def test_embedding_failure_prevents_startup_and_disposes_database(self):
        self.embedding.side_effect = RuntimeError("embedding unavailable")
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("apps.backend.app.dispose_database", new_callable=AsyncMock) as dispose,
        ):
            with self.assertRaisesRegex(RuntimeError, "embedding unavailable"), TestClient(app):
                self.fail("An uninitialized embedding model must not accept requests")
            dispose.assert_awaited_once_with()

    def test_all_invalid_values_are_reported_together(self) -> None:
        with self.assertRaises(ConfigurationError) as raised:
            validate_startup_config(
                {
                    "DATABASE_URL": "sqlite:///local.db",
                    "INFERENCE_BACKEND": "unknown",
                    "LLAMA_SERVER_TIMEOUT": "0",
                }
            )

        message = str(raised.exception)
        self.assertIn("DATABASE_URL must use postgresql+psycopg", message)
        self.assertIn("INFERENCE_BACKEND must be one of", message)
        self.assertIn("LLAMA_SERVER_TIMEOUT must be a positive number", message)

    def test_valid_config_is_normalized(self) -> None:
        settings = validate_startup_config(VALID_ENV)

        self.assertEqual(settings.database_url, VALID_ENV["DATABASE_URL"])
        self.assertEqual(settings.inference_backend, "llama_server")
        self.assertEqual(settings.llama_server_url, "http://localhost:8080")
        self.assertEqual(settings.llama_server_timeout, 30.0)
        self.assertNotIn("test-password", repr(settings))
        self.assertEqual(settings.app_environment, "local")
        self.assertEqual(settings.observability_content_capture, "metadata")

    def test_invalid_observability_values_are_reported_without_secrets(self) -> None:
        env = {
            **VALID_ENV,
            "APP_ENVIRONMENT": "demo",
            "OTEL_TRACING_ENABLED": "sometimes",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "grpc://token:secret@collector",
            "OBSERVABILITY_CONTENT_CAPTURE": "everything",
        }
        with self.assertRaises(ConfigurationError) as raised:
            validate_startup_config(env)
        message = str(raised.exception)
        self.assertIn("APP_ENVIRONMENT", message)
        self.assertIn("OTEL_TRACING_ENABLED", message)
        self.assertIn("OBSERVABILITY_CONTENT_CAPTURE", message)
        self.assertNotIn("secret", message)

    def test_fastapi_lifespan_supports_chat_without_a_database(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with TestClient(app) as client:
                self.assertEqual(client.get('/').status_code, 200)
                self.assertEqual(client.get('/api/heritages').status_code, 503)

    def test_fastapi_lifespan_initializes_and_disposes_database(self) -> None:
        with (
            patch.dict(os.environ, VALID_ENV, clear=True),
            patch("apps.backend.app.configure_database") as configure,
            patch(
                "apps.backend.app.dispose_database", new_callable=AsyncMock
            ) as dispose,
        ):
            with TestClient(app) as client:
                response = client.get("/")

            self.assertEqual(response.status_code, 200)
            configure.assert_called_once_with(VALID_ENV["DATABASE_URL"])
            dispose.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
