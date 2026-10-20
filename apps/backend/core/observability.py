"""Privacy-safe logging, metrics and tracing for the backend."""

from __future__ import annotations

import contextvars
import ipaddress
import json
import logging
import os
import re
import time
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from opentelemetry import context as otel_context, propagate, trace
from opentelemetry.trace import SpanKind, Status, StatusCode
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)
_SECRET = re.compile(
    r"(?i)(password|token|api[_-]?key|authorization)(\s*[=:]\s*)([^\s,;]+)"
)
_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
_IPV6 = re.compile(
    r"(?i)(?<![0-9a-f:])(?:[0-9a-f]{1,4}:){1,7}:?[0-9a-f]{0,4}(?![0-9a-f:])"
)
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\s.-]?){9,15}(?!\w)")
_SENSITIVE_KEY = re.compile(
    r"(?i)password|token|api.?key|authorization|raw.?ip|email|phone|prompt|evidence"
)
_KNOWN_METHODS = frozenset(
    {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "CONNECT", "TRACE"}
)

REQUESTS = Counter(
    "heritage_http_requests_total", "HTTP requests", ["method", "route", "status"]
)
ERRORS = Counter(
    "heritage_http_errors_total", "HTTP errors", ["method", "route", "status"]
)
DURATION = Histogram(
    "heritage_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
DEPENDENCY_HEALTH = Gauge(
    "heritage_dependency_health", "Dependency health", ["dependency"]
)


@contextmanager
def retrieval_stage(name: str):
    """Trace retrieval work without recording questions or source content."""
    with trace.get_tracer(__name__).start_as_current_span(f"retrieval.{name}"):
        yield


def redact(value: Any) -> Any:
    """Remove secrets and common raw personal identifiers recursively."""
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if _SENSITIVE_KEY.search(str(key))
                else redact(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        redacted = _SECRET.sub(r"\1\2[REDACTED]", value)
        redacted = _EMAIL.sub("[REDACTED_EMAIL]", redacted)
        redacted = _IPV4.sub("[REDACTED_IP]", redacted)
        redacted = _IPV6.sub("[REDACTED_IP]", redacted)
        return _PHONE.sub("[REDACTED_PHONE]", redacted)
    return value


_rag_parent: contextvars.ContextVar[Any] = contextvars.ContextVar('rag_parent', default=None)


class RagObservation:
    """Fail-open SDK boundary shared by all RAG stages, including worker threads."""

    def __init__(self, span: Any, mode: str):
        self.span, self.mode = span, mode

    def update(self, **fields: Any) -> None:
        if self.span is None:
            return
        if self.mode != 'full':
            fields = {k: v for k, v in fields.items() if k not in {'input', 'output'}}
        for key in ('input', 'output', 'metadata'):
            if key in fields:
                fields[key] = redact(fields[key])
        try:
            self.span.update(**fields)
        except Exception:
            logging.getLogger(__name__).warning('rag_observation_update_failed')


@contextmanager
def rag_observation(name: str, *, as_type: str = 'span', input: Any = None,
                    metadata: dict | None = None):
    """Explicit parentage avoids auto-recording exception messages or SDK failures."""
    mode = os.environ.get('OBSERVABILITY_CONTENT_CAPTURE', 'metadata')
    parent = _rag_parent.get()
    span = None
    manager = None
    context_token = None
    try:
        client = _langfuse_client() if mode != 'none' else None
        if client is not None:
            if parent is None:
                # Do not give the application root an unexported HTTP parent.
                context_token = otel_context.attach(otel_context.Context())
            context = ({'trace_id': parent.trace_id, 'parent_span_id': parent.id}
                       if parent is not None else None)
            manager = client.start_as_current_observation(name=name, as_type=as_type, trace_context=context)
            span = manager.__enter__()
    except Exception:
        logging.getLogger(__name__).warning('rag_observation_start_failed')
    observation = RagObservation(span, mode)
    observation.update(input=input, metadata=metadata or {})
    token = _rag_parent.set(span)
    try:
        yield observation
    except BaseException as error:
        observation.update(level='ERROR', status_message=type(error).__name__)
        raise
    finally:
        _rag_parent.reset(token)
        if span is not None:
            try:
                # Never hand raw business exceptions to the SDK's recorder.
                manager.__exit__(None, None, None)
            except Exception:
                logging.getLogger(__name__).warning('rag_observation_end_failed')
        if context_token is not None:
            otel_context.detach(context_token)


def grounded_qa_metadata(
    mode: str,
    *,
    model: str,
    corpus_version: str,
    evidence_ids: list[str],
    token_usage: int | None,
    latency_ms: float,
    grounded: bool,
    correlation_id: str,
    prompt: str | None = None,
    evidence: str | None = None,
) -> dict[str, Any]:
    """Build the fail-open Langfuse-compatible grounded-QA observation contract."""
    if mode == "none":
        return {}
    result: dict[str, Any] = {
        "model": model,
        "corpus_version": corpus_version,
        "evidence_ids": evidence_ids,
        "evidence_count": len(evidence_ids),
        "token_usage": token_usage,
        "latency_ms": latency_ms,
        "grounded": grounded,
        "correlation_id": correlation_id,
    }
    if mode == "full":
        result.update(prompt=redact(prompt), evidence=redact(evidence))
    return result


def emit_grounded_qa(
    observe: Callable[[dict[str, Any]], None],
    mode: str,
    **observation: Any,
) -> dict[str, Any]:
    """Send the Langfuse-compatible contract without affecting business requests."""
    metadata = grounded_qa_metadata(mode, **observation)
    if not metadata:
        return metadata
    try:
        observe(metadata)
    except Exception:  # noqa: BLE001 -- observability integrations are fail-open
        logging.getLogger(__name__).warning("grounded_qa_observation_failed")
    return metadata


@lru_cache(maxsize=1)
def _langfuse_client() -> Any | None:
    """Create the optional SDK client only when explicitly enabled."""
    if os.environ.get("LANGFUSE_ENABLED", "false").strip().lower() not in {
        "true", "1", "yes", "on"
    }:
        return None
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
    if not public_key or not secret_key:
        logging.getLogger(__name__).warning("langfuse_credentials_missing")
        return None
    try:
        from langfuse import Langfuse

        return Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=os.environ.get("LANGFUSE_HOST", "http://localhost:3003"),
        )
    except Exception:  # noqa: BLE001 -- optional telemetry must remain fail-open
        logging.getLogger(__name__).warning("langfuse_setup_failed")
        return None


def send_grounded_qa(metadata: dict[str, Any]) -> None:
    """Queue one grounded-QA generation in Langfuse without blocking on flush."""
    parent = _rag_parent.get()
    if parent is not None:
        RagObservation(parent, os.environ.get('OBSERVABILITY_CONTENT_CAPTURE', 'metadata')).update(
            metadata={k: v for k, v in metadata.items() if k not in {'prompt', 'evidence'}},
        )
        return
    client = _langfuse_client()
    if client is None or not metadata:
        return
    content = None
    if "prompt" in metadata or "evidence" in metadata:
        content = {
            "prompt": metadata.get("prompt"),
            "evidence": metadata.get("evidence"),
        }
    safe_metadata = {
        key: value
        for key, value in metadata.items()
        if key not in {"model", "token_usage", "prompt", "evidence"}
    }
    usage = metadata.get("token_usage")
    usage_details = {"total": usage} if isinstance(usage, int) else None
    with client.start_as_current_observation(
        name="grounded-qa",
        as_type="generation",
        model=metadata.get("model"),
        input=content,
        metadata=safe_metadata,
        usage_details=usage_details,
    ):
        pass


def observe_grounded_qa(mode: str, **observation: Any) -> dict[str, Any]:
    """Build and queue the configured privacy-safe Langfuse observation."""
    return emit_grounded_qa(send_grounded_qa, mode, **observation)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": getattr(record, "service", "heritage-api"),
            "environment": getattr(record, "environment", "local"),
            "severity": record.levelname,
            "correlation_id": correlation_id.get(),
            "message": redact(record.getMessage()),
        }
        if record.exc_info:
            payload["error_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(service: str, environment: str) -> None:
    root = logging.getLogger()
    for existing in root.handlers:
        if getattr(existing, "_heritage_json", False):
            return

    handler = logging.StreamHandler()
    handler._heritage_json = True  # type: ignore[attr-defined]
    handler.setFormatter(JsonFormatter())
    handler.addFilter(
        lambda record: (
            setattr(record, "service", service) is None
            and setattr(record, "environment", environment) is None
        )
    )
    root.handlers[:] = [
        existing
        for existing in root.handlers
        if not isinstance(existing, logging.StreamHandler)
    ]
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def _safe_id(value: str | None) -> str:
    try:
        return str(uuid.UUID(value or ""))
    except (ValueError, AttributeError):
        return str(uuid.uuid4())


async def correlation_middleware(request: Request, call_next):
    request_id = _safe_id(request.headers.get("X-Correlation-ID"))
    method = request.method if request.method in _KNOWN_METHODS else "OTHER"
    token = correlation_id.set(request_id)
    started = time.perf_counter()
    status = 500
    parent = propagate.extract(request.headers)
    with trace.get_tracer(__name__).start_as_current_span(
        "http.request", context=parent, kind=SpanKind.SERVER
    ) as span:
        span.set_attribute("correlation.id", request_id)
        span.set_attribute("http.request.method", method)
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        except Exception:
            logging.getLogger("heritage.request").exception("unhandled_request_error")
            response = JSONResponse(
                {"detail": "Internal server error"}, status_code=500
            )
            return response
        finally:
            route = request.scope.get("route")
            route_label = getattr(route, "path", "unmatched")
            span.update_name(f"{method} {route_label}")
            span.set_attribute("http.route", route_label)
            span.set_attribute("http.response.status_code", status)
            if status >= 500:
                span.set_status(Status(StatusCode.ERROR))
            REQUESTS.labels(method, route_label, str(status)).inc()
            if status >= 400:
                ERRORS.labels(method, route_label, str(status)).inc()
            DURATION.labels(method, route_label).observe(
                time.perf_counter() - started
            )
            if "response" in locals():
                response.headers["X-Correlation-ID"] = request_id
            logging.getLogger("heritage.request").info(
                "request_completed method=%s route=%s status=%s",
                method,
                route_label,
                status,
            )
            correlation_id.reset(token)


def metrics_response(request: Request) -> Response:
    """Expose metrics only to loopback/private Docker-network clients."""
    host = request.client.host if request.client else ""
    if host == "testclient":
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    try:
        if not ipaddress.ip_address(host).is_private:
            raise HTTPException(status_code=404)
    except ValueError:
        raise HTTPException(status_code=404) from None
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@dataclass(frozen=True)
class TracingRuntime:
    provider: Any
    httpx_instrumentor: Any
    sqlalchemy_instrumentor: Any | None


def setup_tracing(app: Any, settings: Any, engine: Any = None) -> TracingRuntime | None:
    """Initialize OTLP and auto-instrumentation. Export failures remain fail-open."""
    if not settings.otel_tracing_enabled:
        return None
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(
            resource=Resource.create(
                {
                    "service.name": settings.otel_service_name,
                    "deployment.environment": settings.app_environment,
                }
            )
        )
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=settings.otel_exporter_otlp_endpoint,
                    insecure=settings.otel_exporter_otlp_endpoint.startswith("http://"),
                )
            )
        )
        trace.set_tracer_provider(provider)
        httpx_instrumentor = HTTPXClientInstrumentor()
        httpx_instrumentor.instrument()
        sqlalchemy_instrumentor = None
        if engine is not None:
            sqlalchemy_instrumentor = SQLAlchemyInstrumentor()
            sqlalchemy_instrumentor.instrument(engine=engine.sync_engine)
        return TracingRuntime(provider, httpx_instrumentor, sqlalchemy_instrumentor)
    except Exception:
        logging.getLogger(__name__).warning("tracing_setup_failed", exc_info=True)
        return None


def shutdown_tracing(runtime: TracingRuntime | None) -> None:
    if not runtime:
        return
    try:
        if runtime.sqlalchemy_instrumentor:
            runtime.sqlalchemy_instrumentor.uninstrument()
        runtime.httpx_instrumentor.uninstrument()
        runtime.provider.shutdown()
    except Exception:  # noqa: BLE001 -- telemetry shutdown must remain fail-open
        logging.getLogger(__name__).warning("tracing_shutdown_failed")
