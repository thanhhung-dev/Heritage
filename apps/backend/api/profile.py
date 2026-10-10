from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.db.session import AsyncSessionLocal
from apps.backend.models.user import UserProfile, UserConsent
from apps.backend.schemas.user import (
    UserProfileResponse,
    UserProfileUpdate,
    UserConsentResponse,
    UserConsentUpdate,
)

router = APIRouter(prefix="/api/profile", tags=["Profile & Personalization Consent"])


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_account_id() -> int:
    # Mock auth dependency choice for Subtask HER-165 (default test user account_id = 1)
    return 1


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(
    account_id: int = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserProfile).where(UserProfile.account_id == account_id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile:
        profile = UserProfile(account_id=account_id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


@router.put("/me", response_model=UserProfileResponse)
async def update_profile(
    payload: UserProfileUpdate,
    account_id: int = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserProfile).where(UserProfile.account_id == account_id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile:
        profile = UserProfile(account_id=account_id)
        db.add(profile)

    if payload.display_name is not None:
        profile.display_name = payload.display_name
    if payload.avatar_url is not None:
        profile.avatar_url = payload.avatar_url
    if payload.bio is not None:
        profile.bio = payload.bio

    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/consent", response_model=UserConsentResponse)
async def get_consent(
    account_id: int = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserConsent).where(UserConsent.account_id == account_id)
    result = await db.execute(stmt)
    consent = result.scalar_one_or_none()
    if not consent:
        consent = UserConsent(account_id=account_id, analytics_opt_in=False)
        db.add(consent)
        await db.commit()
        await db.refresh(consent)
    return consent


@router.put("/consent", response_model=UserConsentResponse)
async def update_consent(
    payload: UserConsentUpdate,
    account_id: int = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserConsent).where(UserConsent.account_id == account_id)
    result = await db.execute(stmt)
    consent = result.scalar_one_or_none()
    if not consent:
        consent = UserConsent(account_id=account_id, analytics_opt_in=payload.analytics_opt_in)
        db.add(consent)
    else:
        consent.analytics_opt_in = payload.analytics_opt_in

    await db.commit()
    await db.refresh(consent)
    return consent
