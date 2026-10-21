"""Authenticated current-user information; preserve the existing auth URLs."""
from fastapi import APIRouter, Depends

from apps.backend.common.schemas.auth import ErrorResponse, UserResponse
from apps.backend.common.security import get_current_user

router = APIRouter(prefix='/api/auth', tags=['Authentication'])


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Chưa đăng nhập hoặc token không hợp lệ"},
    },
)
async def get_me(
    current_user: dict = Depends(get_current_user),
) -> UserResponse:
    """Lấy thông tin người dùng hiện tại.

    Args:
        current_user: User information from JWT token

    Returns:
        UserResponse: Thông tin người dùng
    """
    return UserResponse(
        account_id=current_user["sub"],
        email=current_user.get("username", ""),
        username=current_user.get("username", ""),
        role=current_user.get("role", "user"),
    )
