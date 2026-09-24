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

DEFAULT_DATABASE_POOL_SIZE = 10
DEFAULT_DATABASE_MAX_OVERFLOW = 20
DEFAULT_DATABASE_POOL_TIMEOUT = 30.0
DEFAULT_DATABASE_POOL_RECYCLE = 300
DEFAULT_DATABASE_ECHO = False
DEFAULT_DATABASE_SSL_MODE = "disable"
SUPPORTED_DATABASE_SSL_MODES = {
    "disable",
    "allow",
    "prefer",
    "require",
    "verify-ca",
    "verify-full",
}


class ConfigurationError(RuntimeError):
    """Raised when the backend cannot safely start with its environment."""


@dataclass(frozen=True)
class DatabaseSettings:
    """Validated database connection, pool, and TLS settings."""

    url: str = field(repr=False)
    pool_size: int
    max_overflow: int
    pool_timeout: float
    pool_recycle: int
    echo: bool
    ssl_mode: str
    ssl_root_cert: str | None

    @property
    def connect_args(self) -> dict[str, str]:
        args = {"sslmode": self.ssl_mode}
        if self.ssl_root_cert is not None:
            args["sslrootcert"] = self.ssl_root_cert
        return args


@dataclass(frozen=True)
class StartupSettings:
    """Validated settings used to initialize backend runtime resources."""

    database: DatabaseSettings
    inference_backend: str
    llama_server_url: str
    llama_server_timeout: float

    @property
    def database_url(self) -> str:
        """Compatibility accessor that keeps the URL redacted from ``repr``."""

        return self.database.url


def _is_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False


def _read_int(
    env: Mapping[str, str],
    name: str,
    default: int,
    errors: list[str],
    *,
    minimum: int,
) -> int:
    raw = env.get(name, str(default)).strip() or str(default)
    try:
        value = int(raw)
        if value < minimum:
            raise ValueError
        return value
    except ValueError:
        errors.append(f"{name} must be an integer greater than or equal to {minimum}.")
        return default


def _read_float(
    env: Mapping[str, str],
    name: str,
    default: float,
    errors: list[str],
) -> float:
    raw = env.get(name, str(default)).strip() or str(default)
    try:
        value = float(raw)
        if value <= 0:
            raise ValueError
        return value
    except ValueError:
        errors.append(f"{name} must be a positive number.")
        return default


def _read_bool(
    env: Mapping[str, str],
    name: str,
    default: bool,
    errors: list[str],
) -> bool:
    raw = env.get(name, str(default)).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    errors.append(f"{name} must be true or false.")
    return default


def _parse_database_settings(
    env: Mapping[str, str], errors: list[str]
) -> DatabaseSettings:
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

    pool_size = _read_int(
        env,
        "DATABASE_POOL_SIZE",
        DEFAULT_DATABASE_POOL_SIZE,
        errors,
        minimum=1,
    )
    max_overflow = _read_int(
        env,
        "DATABASE_MAX_OVERFLOW",
        DEFAULT_DATABASE_MAX_OVERFLOW,
        errors,
        minimum=0,
    )
    pool_timeout = _read_float(
        env,
        "DATABASE_POOL_TIMEOUT",
        DEFAULT_DATABASE_POOL_TIMEOUT,
        errors,
    )
    pool_recycle = _read_int(
        env,
        "DATABASE_POOL_RECYCLE",
        DEFAULT_DATABASE_POOL_RECYCLE,
        errors,
        minimum=1,
    )
    echo = _read_bool(
        env,
        "DATABASE_ECHO",
        DEFAULT_DATABASE_ECHO,
        errors,
    )

    ssl_mode = (
        env.get("DATABASE_SSL_MODE", DEFAULT_DATABASE_SSL_MODE).strip().lower()
        or DEFAULT_DATABASE_SSL_MODE
    )
    if ssl_mode not in SUPPORTED_DATABASE_SSL_MODES:
        supported = ", ".join(sorted(SUPPORTED_DATABASE_SSL_MODES))
        errors.append(f"DATABASE_SSL_MODE must be one of: {supported}.")

    ssl_root_cert = env.get("DATABASE_SSL_ROOT_CERT", "").strip() or None
    verifies_certificate = ssl_mode in {"verify-ca", "verify-full"}
    if verifies_certificate and ssl_root_cert is None:
        errors.append(
            "DATABASE_SSL_ROOT_CERT is required when DATABASE_SSL_MODE "
            "is verify-ca or verify-full."
        )
    elif verifies_certificate and not Path(ssl_root_cert).expanduser().is_file():
        errors.append("DATABASE_SSL_ROOT_CERT must point to a readable CA file.")
    elif ssl_root_cert is not None and not verifies_certificate:
        errors.append(
            "DATABASE_SSL_ROOT_CERT may only be set with verify-ca or verify-full."
        )

    return DatabaseSettings(
        url=database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        echo=echo,
        ssl_mode=ssl_mode,
        ssl_root_cert=ssl_root_cert,
    )


def _raise_configuration_errors(errors: list[str]) -> None:
    if errors:
        details = "\n".join(f"- {message}" for message in errors)
        raise ConfigurationError(
            f"Backend startup configuration is invalid:\n{details}"
        )


def validate_database_config(
    environ: Mapping[str, str] | None = None,
) -> DatabaseSettings:
    """Validate database-only settings for migrations and import jobs."""

    env = os.environ if environ is None else environ
    errors: list[str] = []
    settings = _parse_database_settings(env, errors)
    _raise_configuration_errors(errors)
    return settings


def validate_startup_config(
    environ: Mapping[str, str] | None = None,
) -> StartupSettings:
    """Validate all runtime configuration and return normalized settings.

    All problems are reported together. Secret values such as ``DATABASE_URL``
    are never included in the error message.
    """

    env = os.environ if environ is None else environ
    errors: list[str] = []
    database = _parse_database_settings(env, errors)

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

    llama_server_timeout = _read_float(
        env,
        "LLAMA_SERVER_TIMEOUT",
        DEFAULT_LLAMA_SERVER_TIMEOUT,
        errors,
    )

    if inference_backend == "llama_server" and not _is_http_url(llama_server_url):
        errors.append("LLAMA_SERVER_URL must be a valid http:// or https:// URL.")

    if inference_backend == "llama_cpp" and not GGUF_MODEL_PATH.is_file():
        errors.append(
            f"INFERENCE_BACKEND=llama_cpp requires a GGUF model at {GGUF_MODEL_PATH}."
        )

    _raise_configuration_errors(errors)

    return StartupSettings(
        database=database,
        inference_backend=inference_backend,
        llama_server_url=llama_server_url,
        llama_server_timeout=llama_server_timeout,
    )

# Server
BACKEND_HOST = "0.0.0.0"
BACKEND_PORT = 8000
