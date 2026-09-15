"""Core LLM module using portable llama.cpp inference.

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


def _load_transformers_peft(model_id: str, adapter_path: str):
    """Load a PEFT adapter directly for local development and evaluation."""
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if torch.cuda.is_available():
        device = "cuda"
        dtype = torch.bfloat16
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
        dtype = torch.float16
    else:
        device = "cpu"
        dtype = torch.float32

    tokenizer = AutoTokenizer.from_pretrained(adapter_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        dtype=dtype,
        device_map=None,
    ).to(device)
    model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()
    return model, tokenizer


def _transformers_generate(model, tokenizer, messages: list[dict], max_tokens: int) -> str:
    """Generate deterministically with the non-thinking template used in training."""
    import torch

    encoded = tokenizer.apply_chat_template(
        messages,
        return_tensors="pt",
        add_generation_prompt=True,
        return_dict=True,
        enable_thinking=False,
    )
    encoded = {key: value.to(model.device) for key, value in encoded.items()}
    with torch.no_grad():
        output = model.generate(
            **encoded,
            max_new_tokens=max_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
        )
    prompt_length = encoded["input_ids"].shape[1]
    return tokenizer.decode(
        output[0][prompt_length:],
        skip_special_tokens=True,
    ).strip()


def _llama_server_generate(messages: list[dict], max_tokens: int) -> str:
    base_url = os.environ.get("LLAMA_SERVER_URL", "http://localhost:8080").rstrip("/")
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
    backend = os.environ.get("INFERENCE_BACKEND", "llama_server")

    if backend == "llama_server":
        return (None, None, "llama_server")

    if backend == "transformers_peft":
        model_id = os.environ.get("HF_MODEL_ID", "Qwen/Qwen3-4B")
        adapter_path = os.environ.get(
            "PEFT_ADAPTER_PATH",
            "models/peft-adapter/checkpoint-125",
        )
        model, tokenizer = _load_transformers_peft(model_id, adapter_path)
        return (model, tokenizer, "transformers_peft")

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


def generate_response(question: str, context: str = "", max_tokens: int = MAX_TOKENS) -> str:
    model, tokenizer, backend = get_model()
    messages = chat_messages(context, question)

    if backend == "llama_server":
        return _llama_server_generate(messages, max_tokens=max_tokens)
    if backend == "transformers_peft":
        return _transformers_generate(
            model,
            tokenizer,
            messages,
            max_tokens=max_tokens,
        )
    return _llama_cpp_generate(model, messages, max_tokens=max_tokens)
