"""Administrator-only account activation/deactivation API."""
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.security import get_auth_db, require_admin
from apps.backend.schemas.account_status import AccountStatusOut, AccountStatusUpdate
from apps.backend.services.account_status import update_account_status

router = APIRouter(prefix="/api/admin/accounts", tags=["Admin accounts"],
                   dependencies=[Depends(require_admin)])


@router.patch("/{account_id}/status", response_model=AccountStatusOut,
              responses={401: {"description": "Invalid session"}, 403: {"description": "Admin required"},
                         404: {"description": "Account not found"}, 503: {"description": "Database unavailable"}})
async def change_status(account_id: Annotated[int, Path(gt=0, lt=2**63)],
                        request: AccountStatusUpdate, db: AsyncSession = Depends(get_auth_db)):
    return await update_account_status(db, account_id, request.is_active)
