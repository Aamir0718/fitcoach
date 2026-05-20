from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sqlfunc
from datetime import date, timedelta
import os, uuid, shutil

from app.database import get_db
from app.models.auth import Auth
from app.models.progress import WeightLog, Badge, ProgressPhoto
from app.models.workout import Workout
from app.core.security import get_current_verified_user
from app.config import settings

router = APIRouter(prefix="/api/progress", tags=["progress"])

BADGE_DEFINITIONS = [
    {"id": "first_sweat",    "name": "First Sweat",    "icon": "🥇", "threshold": 1},
    {"id": "week_warrior",   "name": "Week Warrior",   "icon": "🔥", "threshold": 7},
    {"id": "monthly_beast",  "name": "Monthly Beast",  "icon": "💪", "threshold": 30},
    {"id": "half_century",   "name": "Half Century",   "icon": "⚡", "threshold": 50},
    {"id": "century_club",   "name": "Century Club",   "icon": "👑", "threshold": 100},
]


@router.get("/")
async def get_progress(
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    uid = current_user.id

    # Total workouts
    total_result = await db.execute(
        select(sqlfunc.count()).where(Workout.user_id == uid, Workout.completed == True)
    )
    total = total_result.scalar() or 0

    # Streak
    streak = await _calculate_streak(uid, db)

    # Badges
    badges_result = await db.execute(select(Badge).where(Badge.user_id == uid))
    badges = [{"id": b.badge_id, "name": b.badge_name, "icon": b.badge_icon, "earned_at": b.earned_at.isoformat()} for b in badges_result.scalars().all()]

    # Weight trend (last 60 days)
    weight_result = await db.execute(
        select(WeightLog).where(WeightLog.user_id == uid).order_by(WeightLog.date.asc()).limit(60)
    )
    weight_data = [{"date": str(w.date), "weight": w.weight} for w in weight_result.scalars().all()]
    weight_lost = 0.0
    if len(weight_data) >= 2:
        weight_lost = round(weight_data[0]["weight"] - weight_data[-1]["weight"], 1)

    # Weekly workout counts (last 8 weeks)
    weekly_data = []
    today = date.today()
    for i in range(7, -1, -1):
        week_start = today - timedelta(days=today.weekday() + i * 7)
        week_end   = week_start + timedelta(days=6)
        count_result = await db.execute(
            select(sqlfunc.count()).where(
                Workout.user_id == uid,
                Workout.completed == True,
                Workout.date >= week_start,
                Workout.date <= week_end,
            )
        )
        weekly_data.append({"week": str(week_start), "count": count_result.scalar() or 0})

    # Muscle distribution
    muscle_result = await db.execute(
        select(Workout.muscle_group, sqlfunc.count()).where(
            Workout.user_id == uid, Workout.completed == True
        ).group_by(Workout.muscle_group)
    )
    muscle_dist = {row[0] or "Unknown": row[1] for row in muscle_result.all()}

    # 90-day heatmap
    heatmap = {}
    heatmap_result = await db.execute(
        select(Workout.date).where(
            Workout.user_id == uid,
            Workout.completed == True,
            Workout.date >= today - timedelta(days=89),
        )
    )
    for row in heatmap_result.scalars().all():
        heatmap[str(row)] = heatmap.get(str(row), 0) + 1

    return {
        "total_workouts": total,
        "current_streak": streak,
        "total_weight_lost": weight_lost,
        "badges": badges,
        "weight": {"labels": [w["date"] for w in weight_data], "values": [w["weight"] for w in weight_data]},
        "weekly_workouts": {"labels": [w["week"] for w in weekly_data], "values": [w["count"] for w in weekly_data]},
        "muscle_distribution": muscle_dist,
        "heatmap": heatmap,
    }


@router.post("/weight")
async def log_weight(
    weight: float,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    log = WeightLog(user_id=current_user.id, weight=weight, date=date.today())
    db.add(log)
    await db.commit()
    return {"message": "Weight logged", "weight": weight}


@router.post("/photos", status_code=201)
async def upload_progress_photo(
    file: UploadFile = File(...),
    notes: str = "",
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, WEBP allowed")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"{current_user.id}_{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    photo = ProgressPhoto(
        user_id=current_user.id,
        photo_url=f"/uploads/{filename}",
        date=date.today(),
        notes=notes,
    )
    db.add(photo)
    await db.commit()
    return {"photo_url": photo.photo_url}


@router.get("/photos")
async def get_progress_photos(
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProgressPhoto)
        .where(ProgressPhoto.user_id == current_user.id)
        .order_by(ProgressPhoto.date.asc())
    )
    photos = result.scalars().all()
    return [{"id": p.id, "photo_url": p.photo_url, "date": str(p.date), "notes": p.notes} for p in photos]


async def _calculate_streak(uid: int, db: AsyncSession) -> int:
    today = date.today()
    streak = 0
    check_date = today
    for _ in range(365):
        result = await db.execute(
            select(sqlfunc.count()).where(
                Workout.user_id == uid,
                Workout.completed == True,
                Workout.date == check_date,
            )
        )
        if (result.scalar() or 0) > 0:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    return streak


async def check_and_award_badges(uid: int, total_workouts: int, db: AsyncSession) -> Badge | None:
    """Award new badges based on total workout count. Returns the newly earned badge if any."""
    existing_result = await db.execute(select(Badge.badge_id).where(Badge.user_id == uid))
    existing_ids = {row[0] for row in existing_result.all()}

    for defn in BADGE_DEFINITIONS:
        if total_workouts >= defn["threshold"] and defn["id"] not in existing_ids:
            badge = Badge(
                user_id=uid,
                badge_id=defn["id"],
                badge_name=defn["name"],
                badge_icon=defn["icon"],
            )
            db.add(badge)
            await db.commit()
            return badge
    return None
