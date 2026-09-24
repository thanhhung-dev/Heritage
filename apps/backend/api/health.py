"""Liveness and dependency-aware readiness endpoints."""

from __future__ import annotations

import asyncio
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from apps.backend.core.config import GGUF_MODEL_PATH, PROJECT_ROOT
from apps.backend.db.base import AsyncSessionLocal

router = APIRouter()
logger = logging.getLogger(__name__)


def _corpus_is_ready() -> bool:
    return (
        (PROJECT_ROOT / "corpus" / "locations_index.json").is_file()
        and (PROJECT_ROOT / "corpus" / "wiki_by_location").is_dir()
    )


async def _database_is_ready() -> bool:
    try:
        async with AsyncSessionLocal() as session:
            await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=2.0)
        return True
    except (SQLAlchemyError, OSError, RuntimeError, TimeoutError):
        # Keep connection strings and driver exception details out of logs.
        logger.warning("Database readiness check failed")
        return False


async def _model_is_ready(inference_backend: str) -> bool:
    if inference_backend == "llama_server":
        url = os.environ.get("LLAMA_SERVER_URL", "http://localhost:8080").rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{url}/health")
                response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False
    if inference_backend == "llama_cpp":
        return GGUF_MODEL_PATH.is_file()
    return False


@router.get("/live")
async def live() -> dict[str, str]:
    """Report whether the API process is alive without checking dependencies."""
    return {"status": "live"}


async def _readiness_status() -> dict[str, str | bool]:
    inference_backend = os.environ.get("INFERENCE_BACKEND", "llama_server")
    database_ready, model_ready = await asyncio.gather(
        _database_is_ready(),
        _model_is_ready(inference_backend),
    )
    corpus_ready = _corpus_is_ready()

    status: dict[str, str | bool] = {
        "status": "ready",
        "inference_backend": inference_backend,
        "database_ready": database_ready,
        "model_ready": model_ready,
        "corpus_ready": corpus_ready,
    }
    if not all((database_ready, model_ready, corpus_ready)):
        status["status"] = "not_ready"
    return status


@router.get("/ready")
async def ready() -> dict[str, str | bool]:
    """Report whether the API and all required dependencies can serve traffic."""
    status = await _readiness_status()
    if status["status"] != "ready":
        raise HTTPException(status_code=503, detail=status)
    return status


@router.get("/health")
async def health() -> dict[str, str | bool]:
    """Backward-compatible alias for the readiness endpoint."""
    return await ready()
