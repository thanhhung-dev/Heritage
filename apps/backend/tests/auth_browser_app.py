"""Loopback browser-test app with real auth routes and disposable in-memory data.

Run only with uvicorn apps.backend.tests.auth_browser_app:app --host 127.0.0.1
--port 18928. Never mount this app or its control endpoints in production.
"""
import asyncio
from contextlib import asynccontextmanager
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import delete
from sqlalchemy.pool import StaticPool

from apps.backend.api import auth
from apps.backend.core import security
from apps.backend.models.admin import AccountRole, AdminAccount


@asynccontextmanager
async def lifespan(app):
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(AccountRole.__table__.create)
        await conn.run_sync(AdminAccount.__table__.create)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.factory = factory
    async with factory() as db:
        db.add_all([AccountRole(id=1, name="ADMIN"), AccountRole(id=7, name="USER")])
        await db.commit()
    async def database():
        async with factory() as db:
            yield db
    app.dependency_overrides[auth.get_db] = database
    app.state.mode = "normal"
    app.state.requests = {"register": 0, "login": 0}
    try:
        with patch.object(security, "SECRET_KEY", "synthetic-browser-only-private-key-1234567890"):
            yield
    finally:
        await engine.dispose()
        app.dependency_overrides.clear()


app = FastAPI(lifespan=lifespan)
app.include_router(auth.router)


@app.middleware("http")
async def controlled_failures(request, call_next):
    operation = request.url.path.rsplit("/", 1)[-1]
    if request.method == "POST" and operation in {"register", "login"}:
        app.state.requests[operation] += 1
        await asyncio.sleep(0.15)
        if app.state.mode == "validation":
            return JSONResponse(status_code=422, content={"detail": [{"loc": ["body", "password"], "msg": "Password rejected by server validation"}]})
        if app.state.mode == "unavailable":
            return JSONResponse(status_code=503, content={"detail": "Authentication is temporarily unavailable. Please try again later."})
        if app.state.mode == "malformed":
            return JSONResponse(content={"access_token": "", "user": {}})
    return await call_next(request)


app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:3006"],
                   allow_methods=["POST", "GET", "OPTIONS"], allow_headers=["Content-Type"])


@app.post("/__mode/{mode}")
async def mode(mode: str):
    if mode not in {"normal", "validation", "unavailable", "malformed"}:
        return JSONResponse(status_code=400, content={"detail": "Unknown test mode"})
    app.state.mode = mode
    return {"mode": mode}


@app.get("/__stats")
async def stats():
    return app.state.requests


@app.post("/__reset")
async def reset():
    async with app.state.factory() as db:
        await db.execute(delete(AdminAccount))
        await db.commit()
    app.state.mode = "normal"
    app.state.requests = {"register": 0, "login": 0}
    return {"reset": True}
