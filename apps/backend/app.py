"""FastAPI app chính cho chatbot văn hóa Đà Nẵng - Huế."""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from apps.backend.api import chat, graph, health, heritage, tour
from apps.backend.core.config import validate_startup_config
from apps.backend.core.observability import (
    configure_logging,
    correlation_middleware,
    metrics_response,
    setup_tracing,
    shutdown_tracing,
)
from apps.backend.db.base import configure_database, dispose_database

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = validate_startup_config()
    configure_logging(settings.otel_service_name, settings.app_environment)
    engine = configure_database(settings.database_url)
    tracing = setup_tracing(app, settings, engine)
    app.state.settings = settings
    try:
        yield
    finally:
        shutdown_tracing(tracing)
        await dispose_database()


app = FastAPI(
    title="Heritage",
    description="Heritage desc",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"],
)
app.middleware("http")(correlation_middleware)

app.include_router(health.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(tour.router, prefix="/api")
app.include_router(heritage.router, prefix="/api")


@app.get("/internal/metrics", include_in_schema=False)
async def metrics(request: Request):
    return metrics_response(request)


@app.get("/")
async def root():
    return {
        "name": "Chatbot Văn hóa Đà Nẵng - Huế",
        "docs": "/docs",
        "health": "/api/health",
        "graph": "/api/graph/stats",
    }
