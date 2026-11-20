"""Authentication and resource lifecycle for knowledge-library routes."""
import logging
import math
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Response
from fastapi.security import HTTPBearer
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from apps.backend.core import security
from apps.backend.core.r2_library import KnowledgeR2
from apps.backend.db.base import AsyncSessionLocal

log = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False)


def library_claims(credentials=Depends(bearer)):
    unauthorized = HTTPException(401, "Valid administrator authentication required.",
                                 headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise unauthorized
    if not security.SECRET_KEY or security.SECRET_KEY == "your-secret-key-change-this-in-production":
        raise HTTPException(503, "Configure a private JWT signing key before enabling the knowledge library.")
    payload = security.decode_access_token(credentials.credentials)
    try:
        expires = payload["exp"]
        actor = int(payload["sub"])
        if (isinstance(expires, bool) or not isinstance(expires, (float, int))
                or not math.isfinite(expires) or expires <= datetime.now(timezone.utc).timestamp()
                or not 0 < actor < 2**63 or payload.get("type") not in {None, "access"}):
            raise ValueError
    except (KeyError, ValueError, TypeError, OverflowError):
        raise unauthorized from None
    if str(payload.get("role", "")).lower() != "admin":
        raise HTTPException(403, "Administrator permission required.")
    return actor


async def library_db():
    if AsyncSessionLocal.kw.get("bind") is None:
        raise HTTPException(503, "Knowledge database requires DATABASE_URL and its migration.")
    async with AsyncSessionLocal() as db:
        try:
            yield db
        except SQLAlchemyError:
            await db.rollback()
            log.warning("knowledge_database_unavailable")
            raise HTTPException(503, "Knowledge database unavailable; verify configuration and migrations.") from None


async def library_admin(actor=Depends(library_claims), db=Depends(library_db)):
    account = (await db.execute(text("SELECT a.is_active,a.locked_until,r.name FROM account a "
        "JOIN roles r ON r.id=a.role_id WHERE a.id=:id"), {"id": actor})).mappings().one_or_none()
    locked = account["locked_until"] if account else None
    if locked and locked.tzinfo is None:
        locked = locked.replace(tzinfo=timezone.utc)
    if not account or not account["is_active"] or (locked and locked > datetime.now(timezone.utc)):
        raise HTTPException(401, "Administrative account is unavailable.", headers={"WWW-Authenticate": "Bearer"})
    if str(account["name"]).lower() != "admin":
        raise HTTPException(403, "Current administrator permission required.")
    return actor


def library_storage():
    storage = KnowledgeR2()
    try:
        yield storage
    finally:
        storage.client.close()


def private_response(response: Response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
