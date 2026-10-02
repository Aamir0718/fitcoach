from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/camera")
async def get_camera_config():
    """Public, unauthenticated — the live-session camera screen needs these
    thresholds before a user is necessarily logged in to a long-lived session,
    and there is nothing sensitive in them."""
    return {
        "form_score_good_threshold": settings.FORM_SCORE_GOOD_THRESHOLD,
        "form_score_warn_threshold": settings.FORM_SCORE_WARN_THRESHOLD,
    }
