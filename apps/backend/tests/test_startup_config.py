import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from apps.backend.app import app
from apps.backend.core.config import ConfigurationError, validate_startup_config
from apps.backend.db.base import database_engine_options


VALID_ENV = {
    "DATABASE_URL": (
        "postgresql+psycopg://heritagegraph:test-password@localhost:5433/"
        "heritagegraph"
    ),
    "INFERENCE_BACKEND": "llama_server",
    "LLAMA_SERVER_URL": "http://localhost:8080",
    "LLAMA_SERVER_TIMEOUT": "30",
}


class StartupConfigTests(unittest.TestCase):
    def test_missing_database_url_stops_startup_with_clear_error(self) -> None:
        with self.assertRaises(ConfigurationError) as raised:
            validate_startup_config({})

        message = str(raised.exception)
        self.assertIn("DATABASE_URL is required", message)
        self.assertIn(".env.example", message)

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
        self.assertEqual(settings.database.pool_size, 10)
        self.assertEqual(settings.database.max_overflow, 20)
        self.assertEqual(settings.database.pool_timeout, 30.0)
        self.assertEqual(settings.database.pool_recycle, 300)
        self.assertFalse(settings.database.echo)
        self.assertEqual(settings.database.connect_args, {"sslmode": "disable"})
        self.assertEqual(settings.inference_backend, "llama_server")
        self.assertEqual(settings.llama_server_url, "http://localhost:8080")
        self.assertEqual(settings.llama_server_timeout, 30.0)
        self.assertNotIn("test-password", repr(settings))

    def test_custom_pool_and_verify_full_ssl_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ca_file = Path(directory) / "global-bundle.pem"
            ca_file.write_text("test CA bundle", encoding="utf-8")
            settings = validate_startup_config(
                VALID_ENV
                | {
                    "DATABASE_POOL_SIZE": "5",
                    "DATABASE_MAX_OVERFLOW": "7",
                    "DATABASE_POOL_TIMEOUT": "12.5",
                    "DATABASE_POOL_RECYCLE": "180",
                    "DATABASE_ECHO": "true",
                    "DATABASE_SSL_MODE": "verify-full",
                    "DATABASE_SSL_ROOT_CERT": str(ca_file),
                }
            )

        database = settings.database
        self.assertEqual(database.pool_size, 5)
        self.assertEqual(database.max_overflow, 7)
        self.assertEqual(database.pool_timeout, 12.5)
        self.assertEqual(database.pool_recycle, 180)
        self.assertTrue(database.echo)
        self.assertEqual(
            database.connect_args,
            {"sslmode": "verify-full", "sslrootcert": str(ca_file)},
        )

        engine_options = database_engine_options(database)
        self.assertTrue(engine_options["pool_pre_ping"])
        self.assertTrue(engine_options["hide_parameters"])
        self.assertEqual(engine_options["pool_size"], 5)
        self.assertEqual(engine_options["connect_args"], database.connect_args)

    def test_invalid_database_runtime_settings_do_not_expose_url(self) -> None:
        secret_url = (
            "postgresql+psycopg://heritagegraph:super-secret@localhost:5433/"
            "heritagegraph"
        )
        with self.assertRaises(ConfigurationError) as raised:
            validate_startup_config(
                VALID_ENV
                | {
                    "DATABASE_URL": secret_url,
                    "DATABASE_POOL_SIZE": "0",
                    "DATABASE_MAX_OVERFLOW": "-1",
                    "DATABASE_POOL_TIMEOUT": "never",
                    "DATABASE_POOL_RECYCLE": "0",
                    "DATABASE_ECHO": "verbose",
                    "DATABASE_SSL_MODE": "verify-full",
                }
            )

        message = str(raised.exception)
        self.assertIn("DATABASE_POOL_SIZE", message)
        self.assertIn("DATABASE_SSL_ROOT_CERT is required", message)
        self.assertNotIn("super-secret", message)
        self.assertNotIn(secret_url, message)

    def test_fastapi_lifespan_rejects_missing_required_config(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError):
                with TestClient(app):
                    self.fail("Application must not start without DATABASE_URL")

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
            configure.assert_called_once()
            configured_database = configure.call_args.args[0]
            self.assertEqual(configured_database.url, VALID_ENV["DATABASE_URL"])
            self.assertEqual(configured_database.ssl_mode, "disable")
            dispose.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
