import io
import json
import logging
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from apps.backend.api import chat as chat_api
from apps.backend.app import app
from apps.backend.core.llm import _llama_server_generate
from apps.backend.core import observability as telemetry
from apps.backend.core.observability import (
    DEPENDENCY_HEALTH,
    JsonFormatter,
    correlation_middleware,
    emit_grounded_qa,
    grounded_qa_metadata,
    redact,
    send_grounded_qa,
    setup_tracing,
    shutdown_tracing,
)


class ObservabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_rag_trace_groups_children_and_enforces_capture_mode(self) -> None:
        records = []

        def start(**fields):
            record = dict(fields)
            records.append(record)
            return SimpleNamespace(
                trace_id=fields['trace_context']['trace_id'], id=str(len(records)),
                update=lambda **values: record.update(values), end=lambda: None,
            )

        client = SimpleNamespace(start_observation=start)
        for mode in ('full', 'metadata', 'none'):
            records.clear()
            with (
                patch.dict('os.environ', {'OBSERVABILITY_CONTENT_CAPTURE': mode}),
                patch.object(telemetry, '_langfuse_client', return_value=client),
            ):
                with telemetry.rag_observation('rag.request', input={'question': 'person@example.com'}):
                    with telemetry.rag_observation('generation', as_type='generation') as generation:
                        generation.update(output='answer token=private', metadata={'finish_reason': 'stop'})
            if mode == 'none':
                self.assertEqual(records, [])
                continue
            self.assertEqual(records[1]['trace_context']['parent_span_id'], '1')
            self.assertEqual(records[0]['trace_context']['trace_id'], records[1]['trace_context']['trace_id'])
            self.assertNotIn('person@example.com', repr(records))
            self.assertNotIn('private', repr(records))
            self.assertEqual(records[1]['metadata']['finish_reason'], 'stop')
            if mode == 'full':
                self.assertIn('answer', records[1]['output'])
            else:
                self.assertNotIn('output', records[1])
                self.assertNotIn('input', records[0])

    def test_rag_trace_failure_does_not_swallow_business_error(self) -> None:
        client = Mock()
        client.start_observation.side_effect = RuntimeError('private telemetry error')
        with (
            patch.dict('os.environ', {'OBSERVABILITY_CONTENT_CAPTURE': 'full'}),
            patch.object(telemetry, '_langfuse_client', return_value=client),
            self.assertRaisesRegex(ValueError, 'business error'),
        ):
            with telemetry.rag_observation('rag.request') as observation:
                observation.update(output='safe')
                raise ValueError('business error')

    def test_correlation_header_is_preserved_or_replaced(self) -> None:
        supplied = str(uuid.uuid4())
        response = self.client.get("/", headers={"X-Correlation-ID": supplied})
        self.assertEqual(response.headers["X-Correlation-ID"], supplied)

        replaced = self.client.get("/", headers={"X-Correlation-ID": "raw-user-value"})
        uuid.UUID(replaced.headers["X-Correlation-ID"])
        self.assertNotEqual(replaced.headers["X-Correlation-ID"], "raw-user-value")

    def test_error_is_counted_with_route_template_not_raw_url(self) -> None:
        self.client.get("/not-a-real-route?token=secret")
        metrics = self.client.get("/internal/metrics").text
        self.assertIn(
            'heritage_http_errors_total{method="GET",route="unmatched",status="404"}',
            metrics,
        )
        self.assertNotIn("not-a-real-route", metrics)
        self.assertIn("heritage_http_request_duration_seconds_bucket", metrics)

        self.client.request("BREW", "/not-a-real-route")
        metrics = self.client.get("/internal/metrics").text
        self.assertIn('method="OTHER"', metrics)
        self.assertNotIn('method="BREW"', metrics)

    def test_correlation_header_is_exposed_to_allowed_frontend(self) -> None:
        response = self.client.get(
            "/", headers={"Origin": "http://localhost:3000"}
        )
        self.assertIn(
            "X-Correlation-ID",
            response.headers["Access-Control-Expose-Headers"],
        )

    def test_json_log_schema_and_redaction(self) -> None:
        record = logging.LogRecord(
            "test",
            logging.ERROR,
            "",
            1,
            "token=abc email me@example.com from 203.0.113.7 or +84 912 345 678",
            (),
            None,
        )
        payload = json.loads(JsonFormatter().format(record))
        self.assertEqual(payload["severity"], "ERROR")
        self.assertIn("timestamp", payload)
        self.assertIn("service", payload)
        self.assertIn("environment", payload)
        self.assertNotIn("abc", payload["message"])
        self.assertNotIn("me@example.com", payload["message"])
        self.assertNotIn("203.0.113.7", payload["message"])
        self.assertNotIn("912 345 678", payload["message"])
        self.assertNotIn("2001:db8::1", redact("source 2001:db8::1"))
        self.assertEqual(redact({"password": "secret"}), {"password": "[REDACTED]"})
        self.assertEqual(redact({"raw_ip": "127.0.0.1"}), {"raw_ip": "[REDACTED]"})

    def test_unhandled_error_is_safe_and_keeps_correlation_id(self) -> None:
        failing_app = FastAPI()
        failing_app.middleware("http")(correlation_middleware)

        @failing_app.get("/fail")
        async def fail() -> None:
            raise RuntimeError("token=secret-value email=person@example.com")

        supplied = str(uuid.uuid4())
        output = io.StringIO()
        logger = logging.getLogger("heritage.request")
        handler = logging.StreamHandler(output)
        handler.setFormatter(JsonFormatter())
        previous_handlers = logger.handlers[:]
        previous_propagate = logger.propagate
        logger.handlers[:] = [handler]
        logger.propagate = False
        try:
            response = TestClient(failing_app).get(
                "/fail", headers={"X-Correlation-ID": supplied}
            )
        finally:
            logger.handlers[:] = previous_handlers
            logger.propagate = previous_propagate

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Internal server error"})
        self.assertEqual(response.headers["X-Correlation-ID"], supplied)
        self.assertNotIn("secret-value", output.getvalue())
        self.assertNotIn("person@example.com", output.getvalue())

    def test_privacy_modes_do_not_capture_content_by_default(self) -> None:
        arguments = {
            "model": "qwen",
            "corpus_version": "v1",
            "evidence_ids": ["safe-id"],
            "token_usage": 10,
            "latency_ms": 2.5,
            "grounded": True,
            "correlation_id": "correlation-id",
            "prompt": "private prompt",
            "evidence": "private evidence",
        }
        self.assertEqual(grounded_qa_metadata("none", **arguments), {})
        metadata = grounded_qa_metadata("metadata", **arguments)
        self.assertNotIn("prompt", metadata)
        self.assertNotIn("evidence", metadata)
        self.assertEqual(metadata["evidence_count"], 1)
        self.assertIn("prompt", grounded_qa_metadata("full", **arguments))

        observer = Mock(side_effect=RuntimeError("telemetry unavailable"))
        self.assertEqual(emit_grounded_qa(observer, "metadata", **arguments), metadata)
        observer.assert_called_once_with(metadata)

    def test_full_mode_redacts_content_and_none_does_not_call_observer(self) -> None:
        arguments = {
            "model": "qwen",
            "corpus_version": "1",
            "evidence_ids": ["chunk-1"],
            "token_usage": None,
            "latency_ms": 1.0,
            "grounded": True,
            "correlation_id": "correlation-id",
            "prompt": "email person@example.com token=secret",
            "evidence": "call +84 912 345 678",
        }
        full = grounded_qa_metadata("full", **arguments)
        self.assertNotIn("person@example.com", full["prompt"])
        self.assertNotIn("secret", full["prompt"])
        self.assertNotIn("912 345 678", full["evidence"])

        observer = Mock()
        self.assertEqual(emit_grounded_qa(observer, "none", **arguments), {})
        observer.assert_not_called()

    @patch("apps.backend.core.observability._langfuse_client")
    def test_langfuse_generation_uses_safe_sdk_fields(self, get_client: Mock) -> None:
        client = Mock()
        get_client.return_value = client
        client.start_as_current_observation.return_value.__enter__ = Mock()
        client.start_as_current_observation.return_value.__exit__ = Mock(
            return_value=False
        )
        metadata = {
            "model": "qwen",
            "corpus_version": "1",
            "evidence_ids": ["chunk-1"],
            "evidence_count": 1,
            "token_usage": 12,
            "latency_ms": 4.2,
            "grounded": True,
            "correlation_id": "correlation-id",
        }

        send_grounded_qa(metadata)

        kwargs = client.start_as_current_observation.call_args.kwargs
        self.assertEqual(kwargs["as_type"], "generation")
        self.assertEqual(kwargs["usage_details"], {"total": 12})
        self.assertIsNone(kwargs["input"])
        self.assertNotIn("token_usage", kwargs["metadata"])

    @patch("apps.backend.core.observability._langfuse_client")
    def test_langfuse_full_mode_passes_redacted_content(self, get_client: Mock) -> None:
        client = Mock()
        get_client.return_value = client
        client.start_as_current_observation.return_value.__enter__ = Mock()
        client.start_as_current_observation.return_value.__exit__ = Mock(
            return_value=False
        )

        metadata = grounded_qa_metadata(
            "full",
            model="qwen",
            corpus_version="1",
            evidence_ids=["chunk-1"],
            token_usage=None,
            latency_ms=1.0,
            grounded=True,
            correlation_id="correlation-id",
            prompt="email person@example.com token=secret",
            evidence="private evidence",
        )
        send_grounded_qa(metadata)

        content = client.start_as_current_observation.call_args.kwargs["input"]
        self.assertNotIn("person@example.com", content["prompt"])
        self.assertNotIn("secret", content["prompt"])
        self.assertEqual(content["evidence"], "private evidence")

    @patch.dict(
        "os.environ",
        {"LANGFUSE_ENABLED": "true", "LANGFUSE_PUBLIC_KEY": "", "LANGFUSE_SECRET_KEY": ""},
        clear=False,
    )
    def test_missing_langfuse_credentials_is_a_noop(self) -> None:
        from apps.backend.core.observability import _langfuse_client

        _langfuse_client.cache_clear()
        self.assertIsNone(_langfuse_client())
        _langfuse_client.cache_clear()

    @patch(
        "apps.backend.api.chat.generate_response",
        side_effect=RuntimeError("token=private-dependency-secret"),
    )
    @patch("apps.backend.api.chat.PassageRepository")
    def test_chat_dependency_error_response_is_sanitized(
        self, _retrieve: Mock, _generate: Mock
    ) -> None:
        _retrieve.return_value.search_evidence = AsyncMock(return_value=SimpleNamespace(
            query=SimpleNamespace(ambiguous=False, intent=frozenset(),
                                  search_text="Giới thiệu di sản"),
            evidence=[SimpleNamespace(text="safe context")],
        ))
        async def fake_db():
            yield Mock()

        app.dependency_overrides[chat_api.get_db] = fake_db
        try:
            response = self.client.post(
                "/api/chat", json={"message": "Giới thiệu di sản", "use_rag": True}
            )
        finally:
            app.dependency_overrides.pop(chat_api.get_db, None)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Model trả lời hiện không khả dụng."})
        self.assertNotIn("private-dependency-secret", response.text)

    @patch("apps.backend.core.llm.httpx.post")
    def test_llama_dependency_health_changes_without_content_labels(
        self, post: Mock
    ) -> None:
        post.return_value.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        _llama_server_generate([], 10)
        self.assertEqual(DEPENDENCY_HEALTH.labels("llama")._value.get(), 1)

        post.side_effect = httpx.ConnectError("private dependency detail")
        with self.assertRaises(httpx.ConnectError):
            _llama_server_generate([], 10)
        self.assertEqual(DEPENDENCY_HEALTH.labels("llama")._value.get(), 0)

    @patch("apps.backend.core.llm.httpx.post")
    def test_dependency_span_is_child_of_safe_api_span(self, post: Mock) -> None:
        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        traced_app = FastAPI()
        traced_app.middleware("http")(correlation_middleware)

        @traced_app.get("/trace")
        async def traced_request() -> dict[str, str]:
            return {"answer": _llama_server_generate([], 10)}

        post.return_value.json.return_value = {
            "choices": [{"message": {"content": "private answer"}}]
        }
        with (
            patch(
                "apps.backend.core.observability.trace.get_tracer",
                side_effect=provider.get_tracer,
            ),
            patch(
                "apps.backend.core.llm.trace.get_tracer",
                side_effect=provider.get_tracer,
            ),
        ):
            response = TestClient(traced_app).get("/trace")

        self.assertEqual(response.status_code, 200)
        spans = {span.name: span for span in exporter.get_finished_spans()}
        server_span = spans["GET /trace"]
        dependency_span = spans["llama.generate"]
        self.assertEqual(
            dependency_span.context.trace_id,
            server_span.context.trace_id,
        )
        self.assertEqual(dependency_span.parent.span_id, server_span.context.span_id)
        self.assertNotIn("private answer", repr(dependency_span.attributes))

    @patch(
        "apps.backend.core.llm.httpx.post",
        side_effect=RuntimeError("token=private-span-secret"),
    )
    def test_dependency_error_span_omits_exception_content(self, _post: Mock) -> None:
        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        with (
            patch(
                "apps.backend.core.llm.trace.get_tracer",
                side_effect=provider.get_tracer,
            ),
            self.assertRaises(RuntimeError),
        ):
            _llama_server_generate([], 10)

        span = exporter.get_finished_spans()[0]
        self.assertEqual(span.status.status_code.name, "ERROR")
        self.assertEqual(span.events, ())
        self.assertNotIn("private-span-secret", repr(span.attributes))

    @patch("opentelemetry.instrumentation.sqlalchemy.SQLAlchemyInstrumentor")
    @patch("opentelemetry.instrumentation.httpx.HTTPXClientInstrumentor")
    @patch("opentelemetry.sdk.trace.export.BatchSpanProcessor")
    @patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter")
    @patch("apps.backend.core.observability.trace.set_tracer_provider")
    def test_enabled_tracing_initializes_and_shuts_down_instrumentation(
        self,
        set_provider: Mock,
        exporter: Mock,
        processor: Mock,
        httpx_instrumentor: Mock,
        sqlalchemy_instrumentor: Mock,
    ) -> None:
        settings = Mock(
            otel_tracing_enabled=True,
            otel_service_name="test",
            app_environment="test",
            otel_exporter_otlp_endpoint="http://127.0.0.1:4317",
        )
        engine = Mock(sync_engine=Mock())

        runtime = setup_tracing(app, settings, engine)

        self.assertIsNotNone(runtime)
        exporter.assert_called_once()
        processor.assert_called_once()
        set_provider.assert_called_once()
        httpx_instrumentor.return_value.instrument.assert_called_once_with()
        sqlalchemy_instrumentor.return_value.instrument.assert_called_once_with(
            engine=engine.sync_engine
        )

        shutdown_tracing(runtime)
        httpx_instrumentor.return_value.uninstrument.assert_called_once_with()
        sqlalchemy_instrumentor.return_value.uninstrument.assert_called_once_with()

    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter",
        side_effect=RuntimeError("collector secret"),
    )
    def test_tracing_setup_is_fail_open(self, _: Mock) -> None:
        settings = Mock(
            otel_tracing_enabled=True,
            otel_service_name="test",
            app_environment="test",
            otel_exporter_otlp_endpoint="http://127.0.0.1:4317",
        )
        self.assertIsNone(setup_tracing(app, settings))


if __name__ == "__main__":
    unittest.main()
