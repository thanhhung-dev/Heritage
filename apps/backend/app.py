"""FastAPI app chính cho chatbot văn hóa Đà Nẵng - Huế."""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.backend.api import chat, graph, health, tour
from apps.backend.core.config import validate_startup_config
from apps.backend.db.base import configure_database, dispose_database

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = validate_startup_config()
    configure_database(settings.database)
    app.state.settings = settings
    try:
        yield
    finally:
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
)

app.include_router(health.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(tour.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "Chatbot Văn hóa Đà Nẵng - Huế",
        "docs": "/docs",
        "health": "/api/health",
        "graph": "/api/graph/stats",
    }
