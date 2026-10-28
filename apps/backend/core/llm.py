from __future__ import annotations

import contextvars
import hashlib
import os
from dataclasses import dataclass
from functools import lru_cache

import httpx
from opentelemetry import trace

from apps.backend.core.observability import DEPENDENCY_HEALTH, rag_observation
from apps.backend.core.prompt import chat_messages

MAX_TOKENS = 768
@dataclass(frozen=True)
class GenerationResult:
    answer: str
    truncated: bool = False
    finish_reason: str | None = None


@dataclass(frozen=True)
class GenerationDetails:
    model: str = "unknown"
    token_usage: int | None = None
    finish_reason: str | None = None

    @property
    def truncated(self) -> bool:
        return self.finish_reason == "length"

generation_details: contextvars.ContextVar[GenerationDetails | None] = contextvars.ContextVar(
    "generation_details", default=None
)


def get_generation_details() -> GenerationDetails:
    return generation_details.get() or GenerationDetails()


def _llama_server_generate(messages: list[dict], max_tokens: int) -> str:
    base_url = os.environ.get("LLAMA_SERVER_URL", "http://localhost:8080").rstrip("/")
    timeout = float(os.environ.get("LLAMA_SERVER_TIMEOUT", "300"))
    with trace.get_tracer(__name__).start_as_current_span(
        "llama.generate",
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        span.set_attribute("gen_ai.system", "llama.cpp")
        span.set_attribute("gen_ai.request.max_tokens", max_tokens)
        try:
            response = httpx.post(
                f"{base_url}/v1/chat/completions",
                json={
                    "messages": messages,
                    "temperature": 0.0,
                    "max_tokens": max_tokens,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            usage = payload.get("usage")
            usage = usage if isinstance(usage, dict) else {}
            generation_details.set(
                GenerationDetails(
                    model=payload.get("model") or "llama.cpp",
                    finish_reason=payload['choices'][0].get('finish_reason'),
                    token_usage=(
                        usage.get("total_tokens")
                        if isinstance(usage.get("total_tokens"), int)
                        else None
                    ),
                )
            )
            DEPENDENCY_HEALTH.labels("llama").set(1)
            return payload["choices"][0]["message"]["content"].strip()
        except Exception:
            DEPENDENCY_HEALTH.labels("llama").set(0)
            span.set_attribute("error.type", "llama_dependency_error")
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            raise


def _llama_cpp_generate(model, messages: list[dict], max_tokens: int) -> str:
    output = model.create_chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.0,
        top_p=1.0,
        repeat_penalty=1.0,
    )
    usage = output.get("usage")
    usage = usage if isinstance(usage, dict) else {}
    generation_details.set(
        GenerationDetails(
            model=getattr(model, "model_path", None) or "llama.cpp",
            finish_reason=output['choices'][0].get('finish_reason'),
            token_usage=(
                usage.get("total_tokens")
                if isinstance(usage.get("total_tokens"), int)
                else None
            ),
        )
    )
    return output["choices"][0]["message"]["content"].strip()


@lru_cache(maxsize=1)
def get_model():
    backend = os.environ.get("INFERENCE_BACKEND", "llama_server")

    if backend == "llama_server":
        return (None, None, "llama_server")

    if backend == "llama_cpp":
        from llama_cpp import Llama
        from apps.backend.core.config import GGUF_MODEL_PATH

        if not GGUF_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Chưa có GGUF model tại {GGUF_MODEL_PATH}."
            )

        model = Llama(
            model_path=str(GGUF_MODEL_PATH),
            n_ctx=4096,
            n_gpu_layers=-1,
            verbose=False,
        )
        return (model, None, "llama_cpp")

    raise ValueError(f"INFERENCE_BACKEND không hợp lệ: {backend}")


def generate_response_with_details(
    question: str, context: str = "", max_tokens: int = MAX_TOKENS, *, history: list[dict[str, str]] | None = None,
) -> GenerationResult:
    generation_details.set(GenerationDetails())
    model, _tokenizer, backend = get_model()
    messages = chat_messages(context, question, history=history)

    with rag_observation('generation', as_type='generation', input=messages) as observation:
        observation.update(
            version=hashlib.sha256(messages[0]['content'].encode()).hexdigest(),
            model_parameters={'temperature': 0.0, 'max_tokens': max_tokens},
        )
        if backend == "llama_server":
            answer = _llama_server_generate(messages, max_tokens=max_tokens)
        else:
            answer = _llama_cpp_generate(model, messages, max_tokens=max_tokens)

        details = get_generation_details()
        observation.update(
            output=answer, model=details.model,
            usage_details={'total': details.token_usage} if details.token_usage is not None else None,
            metadata={
                'finish_reason': details.finish_reason,
                'truncated': details.truncated,
                'answer_chars': len(answer),
            },
        )
        return GenerationResult(
            answer=answer,
            truncated=details.truncated,
            finish_reason=details.finish_reason,
        )


def generate_response(
    question: str, context: str = "", max_tokens: int = MAX_TOKENS, *, history: list[dict[str, str]] | None = None,
) -> str:
    return generate_response_with_details(question, context, max_tokens, history=history).answer
