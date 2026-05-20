"""
AI Coach router — handles the main chat endpoint.
Clean separation: routing logic here, AI logic in services/ai_service.py
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
)

router = APIRouter(prefix="/api/coach", tags=["ai_coach"])


@router.post("/chat", response_model=ChatResponse)
async def coach_chat(
    body: ChatRequest,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    # Load profile
    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=400, detail="Profile not found")

    # If onboarding not complete → handle onboarding
    if not profile.onboarding_complete:
        return await handle_onboarding_message(
            user_id=current_user.id,
            message=body.message,
            profile=profile,
            db=db,
        )

    # Get latest recovery zone
    recovery_result = await db.execute(
        select(RecoveryLog)
        .where(RecoveryLog.user_id == current_user.id)
        .order_by(RecoveryLog.created_at.desc())
        .limit(1)
    )
    recovery = recovery_result.scalar_one_or_none()
    zone = recovery.zone if recovery else "green"

    # Classify intent
    intent = classify_intent(body.message)

    # Route to appropriate handler
    if intent in ("start_workout", "next_set", "done_workout", "easy", "hard", "show_plan", "swap"):
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
