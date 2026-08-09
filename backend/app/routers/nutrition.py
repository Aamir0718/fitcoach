from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import date

from app.database import get_db
from app.models.auth import Auth
from app.models.progress import NutritionLog, ActivityLog
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


async def log_nutrition(user_id: int, meal_name: str, calories: float, protein: float, carbs: float, fats: float, source: str, db: AsyncSession):
    """Save nutrition log to database."""
    nutrition_log = NutritionLog(
        user_id=user_id,
        date=date.today(),
        meal_name=meal_name,
        calories=calories,
        protein=protein,
        carbs=carbs,
        fats=fats,
        source=source
    )
    db.add(nutrition_log)
    await db.commit()
    
    # Create activity log
    activity = ActivityLog(
        user_id=user_id,
        activity_type="nutrition",
        title=f"Logged {meal_name}",
        description=f"{calories} kcal, {protein}g protein",
        meta_data={"calories": calories, "protein": protein, "carbs": carbs, "fats": fats},
        date=date.today()
    )
    db.add(activity)
    await db.commit()


@router.get("/today")
async def get_today_nutrition(
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """Sum of everything logged today via /analyze, for the Home dashboard's
    daily nutrition card. There's no stored per-user calorie target, so
    daily_goal is a fixed reasonable default (2000 kcal) rather than
    something computed — flagging that here since it's a real gap, not an
    oversight."""
    today = date.today()
    result = await db.execute(
        select(NutritionLog).where(
            NutritionLog.user_id == current_user.id,
            NutritionLog.date == today,
        )
    )
    logs = result.scalars().all()

    total_calories = sum(l.calories or 0 for l in logs)
    total_protein = sum(l.protein or 0 for l in logs)
    total_carbs = sum(l.carbs or 0 for l in logs)
    total_fats = sum(l.fats or 0 for l in logs)

    return {
        "date": str(today),
        "total_calories": round(total_calories, 1),
        "total_protein": round(total_protein, 1),
        "total_carbs": round(total_carbs, 1),
        "total_fats": round(total_fats, 1),
        "daily_goal": 2000,
        "meals": [
            {
                "id": l.id,
                "meal_name": l.meal_name,
                "calories": l.calories,
                "protein": l.protein,
                "carbs": l.carbs,
                "fats": l.fats,
                "source": l.source,
            }
            for l in logs
        ],
    }


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

        # Log nutrition data to database
        total_calories = result.get('total_calories', 0)
        total_protein = result.get('total_protein', 0)
        total_carbs = result.get('total_carbs', 0)
        total_fats = result.get('total_fats', 0)
        
        # Determine source
        source = "photo" if body.image_base64 else "text"
        
        # Create meal name from foods
        foods = result.get('foods', [])
        meal_name = foods[0].get('name', 'Meal') if foods else 'Meal'
        
        await log_nutrition(
            current_user.id,
            meal_name,
            total_calories,
            total_protein,
            total_carbs,
            total_fats,
            source,
            db
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