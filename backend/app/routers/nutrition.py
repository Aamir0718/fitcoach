from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import logging

from app.database import get_db
from app.models.auth import Auth
from app.core.security import get_current_verified_user
from app.services.ai_service import analyze_food_ai

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/nutrition",
    tags=["nutrition"]
)


class FoodAnalysisRequest(BaseModel):
    food: str = ""
    image_base64: Optional[str] = None


@router.post("/analyze")
async def analyze_food(
    body: FoodAnalysisRequest,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze food using:
    - Typed food description (USDA)
    - Uploaded image (YOLO + USDA)
    """

    if not body.food.strip() and not body.image_base64:
        raise HTTPException(
            status_code=400,
            detail="Provide either a food description or an image."
        )

    try:

        logger.info(
            f"Nutrition request | user={current_user.id} | "
            f"text={bool(body.food.strip())} | "
            f"image={bool(body.image_base64)}"
        )

        result = await analyze_food_ai(
            food_description=body.food.strip(),
            image_base64=body.image_base64
        )

        if result is None:
            raise HTTPException(
                status_code=500,
                detail="Nutrition analysis returned no result."
            )

        if "error" in result:
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )

        logger.info(
            f"Nutrition success | "
            f"foods={len(result.get('foods', []))} | "
            f"calories={result.get('total_calories', 0)}"
        )

        return result

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Nutrition analysis failed")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )