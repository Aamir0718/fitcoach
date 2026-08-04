from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.auth import Auth
from app.models.profile import Profile
from app.schemas.profile import ProfileUpdate, ProfileResponse, SportOnboardRequest, xp_level_info
from app.core.security import get_current_verified_user
from datetime import date

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _enrich_profile(profile: Profile) -> dict:
    data = {
        c.key: getattr(profile, c.key)
        for c in profile.__table__.columns
    }
    info = xp_level_info(profile.xp or 0)
    data["level_name"] = info["level_name"]
    data["xp_to_next"] = info["xp_to_next"]
    data["bmi"] = profile.bmi
    data["active_mode"] = profile.active_mode
    return data


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _enrich_profile(profile)


@router.put("/me", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdate,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = body.model_dump(exclude_none=True)

    # Calculate age from DOB if provided
    if "date_of_birth" in update_data:
        try:
            dob = date.fromisoformat(update_data["date_of_birth"])
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            update_data["age"] = age
        except ValueError:
            pass

    # Pull out explicit onboarding_complete before applying other fields
    explicit_onboarding = update_data.pop("onboarding_complete", None)

    for key, value in update_data.items():
        setattr(profile, key, value)

    # Use explicit value if sent (card-based onboarding always sends True),
    # otherwise auto-detect from required fields
    if explicit_onboarding is not None:
        profile.onboarding_complete = explicit_onboarding
    else:
        required = ["name", "gender", "height", "weight", "goal", "level", "workout_place", "days_per_week"]
        if all(getattr(profile, f) for f in required):
            profile.onboarding_complete = True

    if "weight" in update_data and update_data["weight"]:
        from app.models.progress import WeightLog
        from sqlalchemy import and_
        today_date = date.today()
        existing_log_res = await db.execute(
            select(WeightLog).where(
                and_(
                    WeightLog.user_id == current_user.id,
                    WeightLog.date == today_date
                )
            )
        )
        existing_log = existing_log_res.scalar_one_or_none()
        if existing_log:
            existing_log.weight = update_data["weight"]
        else:
            weight_log = WeightLog(
                user_id=current_user.id,
                weight=update_data["weight"],
                date=today_date
            )
            db.add(weight_log)

    await db.commit()
    await db.refresh(profile)
    return _enrich_profile(profile)


@router.post("/sport-onboard", response_model=ProfileResponse)
async def sport_onboard(
    body: SportOnboardRequest,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile.plays_sport = True
    profile.sport = body.sport
    profile.sport_role = body.role
    profile.sport_position = body.position
    profile.sport_focus = body.focus
    profile.match_frequency = body.match_frequency
    profile.bowling_type = body.bowling_type
    profile.sport_injuries = body.injuries
    profile.sport_onboarding_complete = True

    await db.commit()
    await db.refresh(profile)
    return _enrich_profile(profile)
