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

GGUF_MODEL_PATH = MODELS_DIR / "qwen-fused.gguf"

DEFAULT_INFERENCE_BACKEND = "llama_server"
DEFAULT_LLAMA_SERVER_URL = "http://localhost:8080"
DEFAULT_LLAMA_SERVER_TIMEOUT = 300.0
SUPPORTED_INFERENCE_BACKENDS = {"llama_server", "llama_cpp"}
DEFAULT_APP_ENVIRONMENT = "local"
DEFAULT_OTEL_SERVICE_NAME = "heritage-api"
DEFAULT_OTEL_EXPORTER_OTLP_ENDPOINT = "http://localhost:4317"
SUPPORTED_ENVIRONMENTS = {"local", "test", "staging", "production"}
SUPPORTED_CONTENT_CAPTURE = {"none", "metadata", "full"}

# Frontend origins allowed by the API CORS policy when CORS_ORIGINS is unset.
DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


class ConfigurationError(RuntimeError):
    """Raised when the backend cannot safely start with its environment."""


@dataclass(frozen=True)
class StartupSettings:
    database_url: str = field(repr=False)
    inference_backend: str
    llama_server_url: str
    llama_server_timeout: float
    app_environment: str
    otel_service_name: str
    otel_exporter_otlp_endpoint: str
    otel_tracing_enabled: bool
    observability_content_capture: str
    cors_origins: tuple[str, ...] = field(default_factory=tuple)
    r2_public_base_url: str | None = None
    r2_allowed_asset_hosts: tuple[str, ...] = field(default_factory=tuple)


def _is_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False


def _is_host(value: str) -> bool:
    """A bare host name — no scheme, no path (e.g. assets.heritage.vn)."""
    return bool(value) and "://" not in value and "/" not in value


def cors_origins(environ: Mapping[str, str] | None = None) -> list[str]:
    """Origins allowed by the API CORS policy.

    Reads ``CORS_ORIGINS`` (comma-separated); falls back to the local frontend.
    """
    env = os.environ if environ is None else environ
    raw = env.get("CORS_ORIGINS", "").strip()
    if not raw:
        return list(DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _boolean(
    env: Mapping[str, str], name: str, default: bool, errors: list[str]
) -> bool:
    value = env.get(name, str(default)).strip().lower()
    if value in {"true", "1", "yes", "on"}:
        return True
    if value in {"false", "0", "no", "off"}:
        return False
    errors.append(f"{name} must be a boolean (true/false).")
    return default


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
        errors.append("DATABASE_URL is required; copy .env.example to .env and set it.")
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

    timeout_raw = env.get(
        "LLAMA_SERVER_TIMEOUT", str(DEFAULT_LLAMA_SERVER_TIMEOUT)
    ).strip() or str(DEFAULT_LLAMA_SERVER_TIMEOUT)
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

    app_environment = (
        env.get("APP_ENVIRONMENT", DEFAULT_APP_ENVIRONMENT).strip().lower()
    )
    if app_environment not in SUPPORTED_ENVIRONMENTS:
        supported_environments = ", ".join(sorted(SUPPORTED_ENVIRONMENTS))
        errors.append(f"APP_ENVIRONMENT must be one of: {supported_environments}.")

    otel_service_name = env.get("OTEL_SERVICE_NAME", DEFAULT_OTEL_SERVICE_NAME).strip()
    if not otel_service_name:
        errors.append("OTEL_SERVICE_NAME must not be empty.")

    otel_endpoint = (
        env.get("OTEL_EXPORTER_OTLP_ENDPOINT", DEFAULT_OTEL_EXPORTER_OTLP_ENDPOINT)
        .strip()
        .rstrip("/")
    )
    if not _is_http_url(otel_endpoint):
        errors.append(
            "OTEL_EXPORTER_OTLP_ENDPOINT must be a valid http:// or https:// URL."
        )

    otel_enabled = _boolean(env, "OTEL_TRACING_ENABLED", False, errors)
    capture = env.get("OBSERVABILITY_CONTENT_CAPTURE", "metadata").strip().lower()
    if capture not in SUPPORTED_CONTENT_CAPTURE:
        errors.append(
            "OBSERVABILITY_CONTENT_CAPTURE must be one of: full, metadata, none."
        )

    configured_cors_origins = cors_origins(env)
    for origin in configured_cors_origins:
        if not _is_http_url(origin):
            errors.append(
                "CORS_ORIGINS must be a comma-separated list of "
                "http:// or https:// origins."
            )
            break

    r2_base_raw = env.get("R2_PUBLIC_BASE_URL", "").strip()
    r2_public_base_url: str | None = None
    if r2_base_raw:
        if not _is_http_url(r2_base_raw):
            errors.append(
                "R2_PUBLIC_BASE_URL must be a valid http:// or https:// URL."
            )
        else:
            r2_public_base_url = r2_base_raw.rstrip("/")

    r2_allowed_asset_hosts = tuple(
        host.strip().lower()
        for host in env.get("R2_ALLOWED_ASSET_HOSTS", "").split(",")
        if host.strip()
    )
    for host in r2_allowed_asset_hosts:
        if not _is_host(host):
            errors.append(
                "R2_ALLOWED_ASSET_HOSTS must be a comma-separated list of "
                "host names (no scheme or path)."
            )
            break

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
        app_environment=app_environment,
        otel_service_name=otel_service_name,
        otel_exporter_otlp_endpoint=otel_endpoint,
        otel_tracing_enabled=otel_enabled,
        observability_content_capture=capture,
        cors_origins=tuple(configured_cors_origins),
        r2_public_base_url=r2_public_base_url,
        r2_allowed_asset_hosts=r2_allowed_asset_hosts,
    )


# Server
BACKEND_HOST = "0.0.0.0"
BACKEND_PORT = 8000
