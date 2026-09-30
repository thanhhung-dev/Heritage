"""Core LLM module - hỗ trợ cả MLX (macOS) và llama.cpp (Docker).

INFERENCE_BACKEND=mlx  → dùng MLX (Apple Silicon only, nhanh hơn).
INFERENCE_BACKEND=llama_server → gọi llama.cpp server trong Docker Compose.
INFERENCE_BACKEND=llama_cpp → nhúng llama.cpp trực tiếp trong Python.

Chuyển backend bằng biến môi trường, KHÔNG đổi code caller.
"""
from __future__ import annotations

import os
from functools import lru_cache

import httpx

from backend.core.prompt import chat_messages

MAX_TOKENS = 768


def _mlx_generate(model, tokenizer, messages, max_tokens: int) -> str:
    from mlx_lm import generate
    from mlx_lm.sample_utils import make_sampler

    prompt = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=False,
    )
    return generate(
        model, tokenizer, prompt=prompt, max_tokens=max_tokens,
        sampler=make_sampler(temp=0.0), verbose=False,
    )


def _llama_server_generate(messages: list[dict], max_tokens: int) -> str:
    base_url = os.environ.get("LLAMA_SERVER_URL", "http://llm:8080").rstrip("/")
    timeout = float(os.environ.get("LLAMA_SERVER_TIMEOUT", "300"))
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
    return response.json()["choices"][0]["message"]["content"].strip()


def _llama_cpp_generate(model, messages: list[dict], max_tokens: int) -> str:
    output = model.create_chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.0,
        top_p=1.0,
        repeat_penalty=1.0,
    )
    return output["choices"][0]["message"]["content"].strip()


@lru_cache(maxsize=1)
def get_model():
    backend = os.environ.get("INFERENCE_BACKEND", "mlx")

    if backend == "llama_server":
        return (None, None, "llama_server")

    if backend == "mlx":
        from backend.core.config import BASE_MODEL, LORA_SERVE_PATH
        if not (LORA_SERVE_PATH / "adapters.safetensors").exists():
            raise FileNotFoundError(
                f"Chưa có adapter tại {LORA_SERVE_PATH}. Chạy:\n"
                f"    bash training/select_adapter.sh 0000200"
            )
        from mlx_lm import load
        model, tokenizer = load(BASE_MODEL, adapter_path=str(LORA_SERVE_PATH))
        return (model, tokenizer, "mlx")

    if backend == "llama_cpp":
        from backend.core.config import GGUF_MODEL_PATH
        if not GGUF_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Chưa có GGUF model tại {GGUF_MODEL_PATH}.\n"
                f"Chạy: python scripts/export_gguf.py"
            )
        from llama_cpp import Llama
        model = Llama(
            model_path=str(GGUF_MODEL_PATH),
            n_ctx=4096,
            n_gpu_layers=-1,  # -1 = dùng hết GPU nếu có
            verbose=False,
        )
        return (model, None, "llama_cpp")

    raise ValueError(f"INFERENCE_BACKEND không hợp lệ: {backend}")


def generate_response(question: str, context: str = "", history: list[dict[str, str]] | None = None, *, max_tokens: int = MAX_TOKENS) -> str:
    model, tokenizer, backend = get_model()
    messages = chat_messages(context, question, history=history)
    if backend == "llama_server":
        return _llama_server_generate(messages, max_tokens=max_tokens)
    if backend == "mlx":
        return _mlx_generate(model, tokenizer, messages, max_tokens=max_tokens)
    return _llama_cpp_generate(model, messages, max_tokens=max_tokens)
