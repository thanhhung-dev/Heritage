"""Configuration paths and startup validation for ``apps.backend``."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Paths
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
GRAPHRAG_DIR = PROJECT_ROOT / "graphrag"
EVAL_DIR = PROJECT_ROOT / "pipelines" / "evaluation"

# GGUF model cho Docker/llama.cpp. Sinh ra bằng scripts/export_gguf.py.
GGUF_MODEL_PATH = MODELS_DIR / "qwen-fused.gguf"

DEFAULT_INFERENCE_BACKEND = "llama_server"
DEFAULT_LLAMA_SERVER_URL = "http://localhost:8080"
DEFAULT_LLAMA_SERVER_TIMEOUT = 300.0
SUPPORTED_INFERENCE_BACKENDS = {"llama_server", "llama_cpp"}


class ConfigurationError(RuntimeError):
    """Raised when the backend cannot safely start with its environment."""


@dataclass(frozen=True)
class StartupSettings:
    """Validated settings used to initialize backend runtime resources."""

    database_url: str = field(repr=False)
    inference_backend: str
    llama_server_url: str
    llama_server_timeout: float


def _is_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False


def validate_startup_config(
    environ: Mapping[str, str] | None = None,
) -> StartupSettings:
    """Validate all runtime configuration and return normalized settings.

    All problems are reported together. Secret values such as ``DATABASE_URL``
    are never included in the error message.
    """

    env = os.environ if environ is None else environ
    errors: list[str] = []

    database_url = env.get("DATABASE_URL", "").strip()
    if not database_url:
        errors.append(
            "DATABASE_URL is required; copy .env.example to .env and set it."
        )
    else:
        try:
            parsed_database_url = urlparse(database_url)
            database_url_is_valid = (
                parsed_database_url.scheme == "postgresql+psycopg"
                and bool(parsed_database_url.hostname)
                and bool(parsed_database_url.path.strip("/"))
            )
        except ValueError:
            database_url_is_valid = False

        if not database_url_is_valid:
            errors.append(
                "DATABASE_URL must use "
                "postgresql+psycopg://<user>:<password>@<host>:<port>/<database>."
            )

    inference_backend = (
        env.get("INFERENCE_BACKEND", DEFAULT_INFERENCE_BACKEND).strip()
        or DEFAULT_INFERENCE_BACKEND
    )
    if inference_backend not in SUPPORTED_INFERENCE_BACKENDS:
        supported = ", ".join(sorted(SUPPORTED_INFERENCE_BACKENDS))
        errors.append(f"INFERENCE_BACKEND must be one of: {supported}.")

    llama_server_url = (
        env.get("LLAMA_SERVER_URL", DEFAULT_LLAMA_SERVER_URL).strip()
        or DEFAULT_LLAMA_SERVER_URL
    ).rstrip("/")

    timeout_raw = (
        env.get("LLAMA_SERVER_TIMEOUT", str(DEFAULT_LLAMA_SERVER_TIMEOUT)).strip()
        or str(DEFAULT_LLAMA_SERVER_TIMEOUT)
    )
    try:
        llama_server_timeout = float(timeout_raw)
        if llama_server_timeout <= 0:
            raise ValueError
    except ValueError:
        llama_server_timeout = DEFAULT_LLAMA_SERVER_TIMEOUT
        errors.append("LLAMA_SERVER_TIMEOUT must be a positive number of seconds.")

    if inference_backend == "llama_server" and not _is_http_url(llama_server_url):
        errors.append("LLAMA_SERVER_URL must be a valid http:// or https:// URL.")

    if inference_backend == "llama_cpp" and not GGUF_MODEL_PATH.is_file():
        errors.append(
            f"INFERENCE_BACKEND=llama_cpp requires a GGUF model at {GGUF_MODEL_PATH}."
        )

    if errors:
        details = "\n".join(f"- {message}" for message in errors)
        raise ConfigurationError(
            f"Backend startup configuration is invalid:\n{details}"
        )

    return StartupSettings(
        database_url=database_url,
        inference_backend=inference_backend,
        llama_server_url=llama_server_url,
        llama_server_timeout=llama_server_timeout,
    )

# Server
BACKEND_HOST = "0.0.0.0"
BACKEND_PORT = 8000
