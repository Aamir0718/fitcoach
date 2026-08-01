"""
AI Coach router — handles the main chat endpoint + greeting endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.auth import Auth
from app.models.profile import Profile
from app.models.recovery import RecoveryLog
from app.schemas.workout import ChatRequest, ChatResponse
from app.core.security import get_current_verified_user
from app.services.ai_service import (
    handle_onboarding_message,
    handle_workout_command,
    handle_free_chat,
    classify_intent,
    _build_greeting,
)

router = APIRouter(prefix="/api/coach", tags=["ai_coach"])


async def _load_context(current_user: Auth, db: AsyncSession):
    """Load profile + recovery zone — shared by both endpoints."""
    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=400, detail="Profile not found. Complete onboarding first.")

    recovery_result = await db.execute(
        select(RecoveryLog)
        .where(RecoveryLog.user_id == current_user.id)
        .order_by(RecoveryLog.created_at.desc())
        .limit(1)
    )
    recovery = recovery_result.scalar_one_or_none()
    zone = recovery.zone if recovery else "green"

    return profile, zone


@router.get("/greeting", response_model=ChatResponse)
async def coach_greeting(
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a personalised greeting for the coach tab.
    Call this when the tab opens — no user message required.
    """
    profile, zone = await _load_context(current_user, db)

    if not profile.onboarding_complete:
        return ChatResponse(
            reply=(
                "Hey! Welcome to FitCoach AI 💪\n\n"
                "Let's get you set up. I'll ask a few quick questions to build your personalised plan.\n\n"
                "What's your name?"
            ),
            type="onboarding",
            data={"field": "name", "input_type": "text"}
        )

    return await _build_greeting(current_user.id, profile, zone, db)


@router.post("/chat", response_model=ChatResponse)
async def coach_chat(
    body: ChatRequest,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    profile, zone = await _load_context(current_user, db)

    # If onboarding not complete → handle onboarding
    if not profile.onboarding_complete:
        return await handle_onboarding_message(
            user_id=current_user.id,
            message=body.message,
            profile=profile,
            db=db,
        )

    # Classify intent
    intent = classify_intent(body.message)

    # Route to workout handler for all workout-related intents
    if intent in (
        "start_workout", "next_set", "done_workout",
        "easy", "hard", "show_plan", "swap_muscle", "greeting",
    ):
        return await handle_workout_command(
            user_id=current_user.id,
            message=body.message,
            intent=intent,
            profile=profile,
            zone=zone,
            mode=body.mode or profile.active_mode,
            db=db,
        )

    # Default: free AI chat
    return await handle_free_chat(
        user_id=current_user.id,
        message=body.message,
        profile=profile,
        zone=zone,
        db=db,
    )
