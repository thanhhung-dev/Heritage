"""FastAPI app chính cho chatbot văn hóa Đà Nẵng - Huế."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Authentication reads JWT configuration at import time, so load .env first.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from apps.backend.api import admin_knowledge, auth, chat, graphrag, health, heritage, profile  # noqa: E402
from apps.backend.core.assets import configure_asset_policy  # noqa: E402
from apps.backend.core.config import cors_origins, validate_startup_config  # noqa: E402
from apps.backend.core.email import EmailConfig, init_email_service  # noqa: E402
from apps.backend.core.observability import (  # noqa: E402
    configure_logging,
    correlation_middleware,
    metrics_response,
    setup_tracing,
    shutdown_tracing,
)
from apps.backend.db.base import configure_database, dispose_database  # noqa: E402

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = validate_startup_config()
    configure_logging(settings.otel_service_name, settings.app_environment)
    engine = configure_database(settings.database_url) if settings.database_url else None
    configure_asset_policy(settings.r2_public_base_url, settings.r2_allowed_asset_hosts)
    
    # Initialize email service
    if settings.smtp_host and settings.smtp_port and settings.smtp_user and settings.smtp_password and settings.smtp_sender_email:
        email_config = EmailConfig(
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            smtp_user=settings.smtp_user,
            smtp_password=settings.smtp_password,
            sender_email=settings.smtp_sender_email,
            sender_name=settings.smtp_sender_name,
            use_tls=settings.smtp_use_tls,
        )
        init_email_service(email_config)
        log.info(f"Email service initialized: {settings.smtp_host}:{settings.smtp_port}")
    else:
        init_email_service(None)
        log.warning("Email service disabled - SMTP not configured in .env")
    
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
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"],
)
app.middleware("http")(correlation_middleware)

app.include_router(auth.router)  # prefix="/api/auth" already in router
app.include_router(health.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(graphrag.router, prefix="/api")
app.include_router(admin_knowledge.router, prefix="/api")
app.include_router(heritage.router, prefix="/api")
app.include_router(profile.router)


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
