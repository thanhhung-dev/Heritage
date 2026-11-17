"""Admin credential endpoints, outside the protected knowledge router."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.security import bearer_token, decode_access_token, get_auth_db
from apps.backend.schemas.auth import AdminLoginRequest, ErrorResponse, LoginResponse
from apps.backend.services.admin_auth import login_admin, logout_admin

router = APIRouter(prefix="/api/admin", tags=["Admin authentication"])
errors = {
    401: {"model": ErrorResponse, "description": "Missing, invalid or expired credentials"},
    403: {"model": ErrorResponse, "description": "Administrator permission required"},
    503: {"model": ErrorResponse, "description": "Authentication configuration or database unavailable"},
}


@router.post("/login", response_model=LoginResponse, responses=errors)
async def login(request: AdminLoginRequest, response: Response, db: AsyncSession = Depends(get_auth_db)):
    """Sign in an active, unlocked account whose current database role is ADMIN."""
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return await login_admin(db, request)


@router.post("/logout", status_code=204, responses=errors)
async def logout(token: str = Depends(bearer_token), db: AsyncSession = Depends(get_auth_db)):
    """Revoke only this bearer token. Repeated logout returns 204 until expiry."""
    await logout_admin(db, token, decode_access_token(token))
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
