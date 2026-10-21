"""Health check endpoint."""
import os

import httpx
from fastapi import APIRouter, HTTPException

from apps.backend.core.config import GGUF_MODEL_PATH

router = APIRouter()


@router.get("/health")
def health():
    inference_backend = os.environ.get("INFERENCE_BACKEND", "llama_server")
    skip_model = os.environ.get("HEALTHCHECK_SKIP_MODEL", "").strip().lower() in ("1", "true", "yes")

    if skip_model:
        model_ready = True
    elif inference_backend == "llama_server":
        url = os.environ.get("LLAMA_SERVER_URL", "http://localhost:8080").rstrip("/")
        try:
            response = httpx.get(f"{url}/health", timeout=2.0)
            response.raise_for_status()
            model_ready = True
        except httpx.HTTPError:
            model_ready = False
    elif inference_backend == "llama_cpp":
        model_ready = GGUF_MODEL_PATH.is_file()
    else:
        model_ready = False

    status = {
        "status": "ok",
        "inference_backend": inference_backend,
        "model_ready": model_ready,
    }
    if not model_ready:
        status["status"] = "starting"
        raise HTTPException(status_code=503, detail=status)
    return status
