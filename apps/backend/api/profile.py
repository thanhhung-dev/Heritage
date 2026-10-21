"""Profile & Personalization Consent API — also serves the Badges/Milestones tabs."""
from typing import AsyncGenerator
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.core.security import get_current_user
from apps.backend.db.base import AsyncSessionLocal
from apps.backend.models.user import UserConsent, UserProfile
from apps.backend.schemas.user import (
    BadgeResponse,
    MilestoneLevelResponse,
    UserConsentResponse,
    UserConsentUpdate,
    UserProfileResponse,
    UserProfileUpdate,
)
from apps.backend.services.gamification import GamificationService

router = APIRouter(prefix="/api/profile", tags=["Profile & Personalization Consent"])


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_account_id(current_user: dict = Depends(get_current_user)) -> int:
    """Resolve the authenticated account id from the JWT ``sub`` claim."""
    try:
        return int(current_user["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(
    account_id: int = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("SELECT account_id, full_name, avatar_url, about, address, personal_link "
             "FROM profiles WHERE account_id = :account_id"),
        {"account_id": account_id},
    )
    profile = result.mappings().one_or_none()
    if profile is None:
        await db.execute(
            text("INSERT INTO profiles (account_id) VALUES (:account_id)"),
            {"account_id": account_id},
        )
        await db.commit()
        profile = {"full_name": None, "avatar_url": None, "about": None, "address": None}
    return {
        "display_name": profile["full_name"],
        "handle": None,
        "avatar_url": profile["avatar_url"],
        "banner_url": None,
        "bio": profile["about"],
        "country": None,
        "city": profile["address"],
        "display_email": False,
        "created_at": datetime.now(),
        "socials": None,
        "total_hours": 0,
        "level": None,
        "featured_badges": None,
        "show_activity_on_profile": True,
    }



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

    if payload.handle is not None:
        existing = await db.execute(
            select(UserProfile).where(
                UserProfile.handle == payload.handle, UserProfile.account_id != account_id
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This username is already taken.",
            )

    for field in (
        "display_name", "handle", "avatar_url", "banner_url", "bio",
        "country", "city", "display_email", "show_activity_on_profile",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(profile, field, value)

    if payload.socials is not None:
        profile.socials = payload.socials.model_dump(exclude_none=True)
    if payload.featured_badges is not None:
        profile.featured_badges = payload.featured_badges

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


@router.get("/badges", response_model=list[BadgeResponse])
async def get_badges(
    account_id: int = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
):
    service = GamificationService(db)
    return await service.list_badges(account_id)


@router.get("/milestones", response_model=list[MilestoneLevelResponse])
async def get_milestones(
    account_id: int = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
):
    service = GamificationService(db)
    return await service.list_milestones(account_id)

