from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sqlfunc, and_, or_
from datetime import date, timedelta, datetime
import os, uuid, shutil

from app.database import get_db
from app.models.auth import Auth
from app.models.progress import WeightLog, Badge, ProgressPhoto, NutritionLog, Streak, PersonalRecord, ActivityLog
from app.models.workout import Workout
from app.models.recovery import RecoveryLog
from app.models.profile import Profile
from app.core.security import get_current_verified_user
from app.config import settings

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("/dashboard")
async def get_progress_dashboard(
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    uid = current_user.id
    today_dt = date.today()

    # 1. Fetch all completed workouts
    all_completed_result = await db.execute(
        select(Workout).where(Workout.user_id == uid, Workout.completed == True)
    )
    all_completed = all_completed_result.scalars().all()

    # 2. Calculate streaks from completed workouts history
    completed_dates = sorted(list({w.date for w in all_completed}), reverse=True)
    current_streak = 0
    best_streak = 0

    if completed_dates:
        today = date.today()
        yesterday = today - timedelta(days=1)
        # Check if latest workout is today or yesterday
        if completed_dates[0] == today or completed_dates[0] == yesterday:
            current_streak = 1
            check_date = completed_dates[0] - timedelta(days=1)
            for d in completed_dates[1:]:
                if d == check_date:
                    current_streak += 1
                    check_date -= timedelta(days=1)
                elif d < check_date:
                    break

        # Calculate longest run of days
        dates_asc = sorted(completed_dates)
        best_streak = 0
        temp_streak = 0
        prev_date = None
        for d in dates_asc:
            if prev_date is None:
                temp_streak = 1
            else:
                diff = (d - prev_date).days
                if diff == 1:
                    temp_streak += 1
                elif diff > 1:
                    if temp_streak > best_streak:
                        best_streak = temp_streak
                    temp_streak = 1
            prev_date = d
        if temp_streak > best_streak:
            best_streak = temp_streak
        best_streak = max(current_streak, best_streak)

        # Sync back to Streak table for database integrity/consistency
        streak_result = await db.execute(select(Streak).where(Streak.user_id == uid))
        streak_record = streak_result.scalar_one_or_none()
        if streak_record:
            streak_record.current_streak = current_streak
            streak_record.longest_streak = best_streak
            streak_record.last_workout_date = completed_dates[0]
        else:
            streak_record = Streak(
                user_id=uid,
                current_streak=current_streak,
                longest_streak=best_streak,
                last_workout_date=completed_dates[0]
            )
            db.add(streak_record)
        await db.commit()

    # 3. Parse exercise counts and muscle group distributions
    exercise_counts = {}
    muscle_counts = {}
    total_workouts = 0
    total_duration = 0

    for w in all_completed:
        total_workouts += 1
        total_duration += w.duration or 0
        
        w_muscle = w.muscle_group or "Full Body"
        w_muscle = w_muscle.replace(" Volume", "").replace(" Strength", "").strip()
        w_muscle = w_muscle.title()

        # Update exercise counts and exercise muscle groups
        if w.exercises:
            for ex in w.exercises:
                ex_name = ex.get("name", "").strip()
                if ex_name:
                    exercise_counts[ex_name] = exercise_counts.get(ex_name, 0) + 1
                    ex_muscle = ex.get("muscle") or ex.get("category") or w_muscle
                    ex_muscle = ex_muscle.capitalize()
                    muscle_counts[ex_muscle] = muscle_counts.get(ex_muscle, 0) + 1
        elif w.exercises_done:
            for ex_name in w.exercises_done.split(","):
                ex_name = ex_name.strip()
                if ex_name:
                    exercise_counts[ex_name] = exercise_counts.get(ex_name, 0) + 1
                    muscle_counts[w_muscle] = muscle_counts.get(w_muscle, 0) + 1
        else:
            # Fallback counts workout muscle
            muscle_counts[w_muscle] = muscle_counts.get(w_muscle, 0) + 1

    # Format muscle_groups as list of dicts: [{"muscle": "Chest", "count": 12}, ...]
    muscle_groups = [{"muscle": k, "count": v} for k, v in muscle_counts.items()]
    muscle_groups = sorted(muscle_groups, key=lambda x: x["count"], reverse=True)

    # 4. Today's Workout detail object
    today_workout = None
    today_workouts = [w for w in all_completed if w.date == today_dt]
    if today_workouts:
        w_today = sorted(today_workouts, key=lambda x: x.created_at or datetime.min, reverse=True)[0]
        num_ex = 0
        if w_today.exercises:
            num_ex = len(w_today.exercises)
        elif w_today.exercises_done:
            num_ex = len([e for e in w_today.exercises_done.split(",") if e.strip()])
        else:
            num_ex = 1

        today_workout = {
            "name": w_today.muscle_group or "Workout",
            "exercises": num_ex,
            "duration": w_today.duration or 0,
            "calories": int(w_today.calories_estimate) if w_today.calories_estimate else int((w_today.duration or 0) * 8.5),
            "status": "Completed"
        }

    # 5. Recent Workouts (latest 5)
    recent_workouts = []
    sorted_completed = sorted(all_completed, key=lambda x: (x.date, x.created_at or datetime.min), reverse=True)
    for w in sorted_completed[:5]:
        num_ex = 0
        if w.exercises:
            num_ex = len(w.exercises)
        elif w.exercises_done:
            num_ex = len([e for e in w.exercises_done.split(",") if e.strip()])
        else:
            num_ex = 1

        completion_time = w.created_at.strftime("%I:%M %p") if w.created_at else "N/A"
        
        recent_workouts.append({
            "name": w.muscle_group or "Workout",
            "completion_time": completion_time,
            "duration": w.duration or 0,
            "calories": int(w.calories_estimate) if w.calories_estimate else int((w.duration or 0) * 8.5),
            "exercises": num_ex
        })

    # 6. Mon-Sun weekly activity timeline checkmark representation
    monday = today_dt - timedelta(days=today_dt.weekday())
    weekly_activity = []
    days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    for i in range(7):
        day_date = monday + timedelta(days=i)
        day_name = days_of_week[i]
        
        # Check workout on this day
        day_workout = next((w for w in all_completed if w.date == day_date), None)
        
        if day_workout:
            num_ex = 0
            if day_workout.exercises:
                num_ex = len(day_workout.exercises)
            elif day_workout.exercises_done:
                num_ex = len([e for e in day_workout.exercises_done.split(",") if e.strip()])
            else:
                num_ex = 1
                
            weekly_activity.append({
                "day": day_name,
                "completed": True,
                "name": day_workout.muscle_group or "Workout",
                "duration": day_workout.duration or 0,
                "exercises": num_ex
            })
        else:
            weekly_activity.append({
                "day": day_name,
                "completed": False,
                "name": None,
                "duration": 0,
                "exercises": 0
            })

    # 7. Weight trend logs
    weight_res = await db.execute(
        select(WeightLog).where(WeightLog.user_id == uid).order_by(WeightLog.date.asc()).limit(30)
    )
    weight_history = [{"date": str(w.date), "weight": w.weight} for w in weight_res.scalars().all()]
    
    profile_result = await db.execute(select(Profile).where(Profile.user_id == uid))
    profile = profile_result.scalar_one_or_none()
    current_weight = profile.weight if profile and profile.weight else None
    
    if not current_weight and weight_history:
        current_weight = weight_history[-1]["weight"]

    return {
        "current_streak": current_streak,
        "best_streak": best_streak,
        "today_workout": today_workout,
        "recent_workouts": recent_workouts,
        "weekly_activity": weekly_activity,
        "exercise_counts": exercise_counts,
        "muscle_groups": muscle_groups,
        "weight_history": weight_history,
        "total_workouts": total_workouts,
        "total_duration": total_duration,
        "current_weight": current_weight
    }

BADGE_DEFINITIONS = [
    {"id": "first_sweat",    "name": "First Sweat",    "icon": "🥇", "threshold": 1},
    {"id": "week_warrior",   "name": "Week Warrior",   "icon": "🔥", "threshold": 7},
    {"id": "monthly_beast",  "name": "Monthly Beast",  "icon": "💪", "threshold": 30},
    {"id": "half_century",   "name": "Half Century",   "icon": "⚡", "threshold": 50},
    {"id": "century_club",   "name": "Century Club",   "icon": "👑", "threshold": 100},
    {"id": "streak_master",  "name": "Streak Master",  "icon": "🔥", "threshold": 7},
    {"id": "nutrition_pro",  "name": "Nutrition Pro",  "icon": "🥗", "threshold": 10},
    {"id": "recovery_king",  "name": "Recovery King",  "icon": "🛌", "threshold": 10},
]


@router.get("/analytics")
async def get_analytics(
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """Comprehensive analytics endpoint for the Progress dashboard."""
    uid = current_user.id
    today = date.today()

    # === Summary Cards ===
    
    # Current streak from Streak model
    streak_result = await db.execute(select(Streak).where(Streak.user_id == uid))
    streak_record = streak_result.scalar_one_or_none()
    current_streak = streak_record.current_streak if streak_record else 0
    longest_streak = streak_record.longest_streak if streak_record else 0

    # Total workouts completed
    total_workouts_result = await db.execute(
        select(sqlfunc.count()).where(Workout.user_id == uid, Workout.completed == True)
    )
    total_workouts = total_workouts_result.scalar() or 0

    # Total workout time (hours)
    total_duration_result = await db.execute(
        select(sqlfunc.sum(Workout.duration)).where(Workout.user_id == uid, Workout.completed == True)
    )
    total_minutes = total_duration_result.scalar() or 0
    total_hours = round(total_minutes / 60, 1)

    # Current weight from profile or latest weight log
    profile_result = await db.execute(select(Profile).where(Profile.user_id == uid))
    profile = profile_result.scalar_one_or_none()
    current_weight = profile.weight if profile and profile.weight else None
    
    if not current_weight:
        latest_weight_result = await db.execute(
            select(WeightLog).where(WeightLog.user_id == uid).order_by(WeightLog.date.desc()).limit(1)
        )
        latest_weight = latest_weight_result.scalar_one_or_none()
        current_weight = latest_weight.weight if latest_weight else None

    # === Weight History ===
    weight_result = await db.execute(
        select(WeightLog).where(WeightLog.user_id == uid).order_by(WeightLog.date.asc()).limit(365)
    )
    weight_data = [{"date": str(w.date), "weight": w.weight} for w in weight_result.scalars().all()]

    # === Workout Calendar (last 90 days) ===
    workout_calendar = {}
    calendar_result = await db.execute(
        select(Workout.date, Workout.muscle_group, Workout.duration).where(
            Workout.user_id == uid,
            Workout.completed == True,
            Workout.date >= today - timedelta(days=89),
        )
    )
    for row in calendar_result.all():
        workout_calendar[str(row[0])] = {
            "muscle_group": row[1] or "Workout",
            "duration": row[2] or 0
        }

    # === Activity Heatmap (GitHub-style, 365 days) ===
    heatmap = {}
    heatmap_result = await db.execute(
        select(Workout.date, Workout.muscle_group, Workout.duration).where(
            Workout.user_id == uid,
            Workout.completed == True,
            Workout.date >= today - timedelta(days=364),
        )
    )
    for row in heatmap_result.all():
        date_str = str(row[0])
        if date_str not in heatmap:
            heatmap[date_str] = {"count": 0, "workouts": []}
        heatmap[date_str]["count"] += 1
        heatmap[date_str]["workouts"].append({
            "muscle_group": row[1] or "Workout",
            "duration": row[2] or 0
        })

    # === Muscle Distribution (this month) ===
    month_start = today.replace(day=1)
    muscle_result = await db.execute(
        select(Workout.muscle_group, sqlfunc.count()).where(
            Workout.user_id == uid,
            Workout.completed == True,
            Workout.date >= month_start,
        ).group_by(Workout.muscle_group)
    )
    muscle_dist = {row[0] or "Unknown": row[1] for row in muscle_result.all()}

    # === Personal Records ===
    pr_result = await db.execute(
        select(PersonalRecord).where(PersonalRecord.user_id == uid).order_by(PersonalRecord.updated_at.desc()).limit(20)
    )
    personal_records = [
        {
            "exercise": pr.exercise_name,
            "best_weight_kg": pr.best_weight_kg,
            "best_reps": pr.best_reps,
            "best_weight_date": str(pr.best_weight_date) if pr.best_weight_date else None,
            "best_reps_date": str(pr.best_reps_date) if pr.best_reps_date else None,
        }
        for pr in pr_result.scalars().all()
    ]

    # === Recent Activity Timeline (last 7 days) ===
    activity_result = await db.execute(
        select(ActivityLog).where(
            ActivityLog.user_id == uid,
            ActivityLog.date >= today - timedelta(days=6),
        ).order_by(ActivityLog.date.desc(), ActivityLog.created_at.desc()).limit(50)
    )
    activities = [
        {
            "type": act.activity_type,
            "title": act.title,
            "description": act.description,
            "meta_data": act.meta_data,
            "date": str(act.date),
        }
        for act in activity_result.scalars().all()
    ]

    # === Achievements/Badges ===
    badges_result = await db.execute(
        select(Badge).where(Badge.user_id == uid).order_by(Badge.earned_at.desc())
    )
    badges = [
        {"id": b.badge_id, "name": b.badge_name, "icon": b.badge_icon, "earned_at": b.earned_at.isoformat()}
        for b in badges_result.scalars().all()
    ]

    # === Monthly Insights ===
    last_month_start = (today.replace(day=1) - timedelta(days=32)).replace(day=1)
    
    # Workouts this month
    this_month_workouts_result = await db.execute(
        select(sqlfunc.count()).where(
            Workout.user_id == uid,
            Workout.completed == True,
            Workout.date >= month_start,
        )
    )
    this_month_workouts = this_month_workouts_result.scalar() or 0

    # Most trained muscle this month
    most_muscle_result = await db.execute(
        select(Workout.muscle_group, sqlfunc.count()).where(
            Workout.user_id == uid,
            Workout.completed == True,
            Workout.date >= month_start,
        ).group_by(Workout.muscle_group).order_by(sqlfunc.count().desc()).limit(1)
    )
    most_muscle_row = most_muscle_result.first()
    most_trained_muscle = most_muscle_row[0] if most_muscle_row else None

    # Average workout duration this month vs last month
    avg_duration_this_month_result = await db.execute(
        select(sqlfunc.avg(Workout.duration)).where(
            Workout.user_id == uid,
            Workout.completed == True,
            Workout.date >= month_start,
        )
    )
    avg_duration_this_month = avg_duration_this_month_result.scalar() or 0

    avg_duration_last_month_result = await db.execute(
        select(sqlfunc.avg(Workout.duration)).where(
            Workout.user_id == uid,
            Workout.completed == True,
            Workout.date >= last_month_start,
            Workout.date < month_start,
        )
    )
    avg_duration_last_month = avg_duration_last_month_result.scalar() or 0

    duration_change = 0
    if avg_duration_last_month > 0:
        duration_change = round(((avg_duration_this_month - avg_duration_last_month) / avg_duration_last_month) * 100, 1)

    # Total protein this month
    protein_result = await db.execute(
        select(sqlfunc.sum(NutritionLog.protein)).where(
            NutritionLog.user_id == uid,
            NutritionLog.date >= month_start,
        )
    )
    total_protein = protein_result.scalar() or 0

    return {
        "summary": {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_workouts": total_workouts,
            "total_workout_hours": total_hours,
            "current_weight": current_weight,
        },
        "weight_history": weight_data,
        "workout_calendar": workout_calendar,
        "heatmap": heatmap,
        "muscle_distribution": muscle_dist,
        "personal_records": personal_records,
        "recent_activity": activities,
        "badges": badges,
        "monthly_insights": {
            "workouts_this_month": this_month_workouts,
            "most_trained_muscle": most_trained_muscle,
            "avg_duration_change_percent": duration_change,
            "total_protein_grams": total_protein,
        },
    }


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
