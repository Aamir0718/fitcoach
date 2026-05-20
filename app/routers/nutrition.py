from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import base64

from app.database import get_db
from app.models.auth import Auth
from app.core.security import get_current_verified_user
from app.services.ai_service import analyze_food_ai

router = APIRouter(prefix="/api/nutrition", tags=["nutrition"])


class FoodAnalysisRequest(BaseModel):
    food: str
    image_base64: Optional[str] = None   # base64-encoded image for photo analysis


@router.post("/analyze")
async def analyze_food(
    body: FoodAnalysisRequest,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.food and not body.image_base64:
        raise HTTPException(status_code=400, detail="Provide food description or image")

    result = await analyze_food_ai(
        food_description=body.food,
        image_base64=body.image_base64,
    )
    return result
