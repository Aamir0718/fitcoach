from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sqlfunc, desc
from datetime import date, timedelta
import random
import re


def _safe_int(value) -> int:
    """Coerce a set's reps/weight to an int, no matter what shape it arrives
    in. The ghost-trainer session logs sets as {reps: ex.reps, weight: 0}
    where ex.reps is a raw string like "12", "3x12" or "30s" (whatever the
    plan's rep scheme says) — `total_reps += "12"` crashes with a
    TypeError *before* the workout row is ever inserted, so the request
    500s and nothing gets saved, silently, since the frontend never checks
    the response status on this call."""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else 0

from app.database import get_db
from app.models.auth import Auth
from app.models.workout import Workout, PlannedWorkout, WeeklyPlan, AIMemory, Exercise, SetLog, FCMToken
from app.models.profile import Profile
from app.models.progress import ActivityLog, Streak, PersonalRecord
from app.schemas.workout import (
    WorkoutLogRequest, WorkoutResponse, SlotSelectRequest, WorkoutFinishRequest,
    SetLogRequest, SetLogResponse, ProgressiveOverloadResponse,
    FCMTokenRequest, ExerciseSwapRequest, RegeneratePlanRequest,
)
from app.core.security import get_current_verified_user
from app.routers.progress import check_and_award_badges

router = APIRouter(prefix="/api/workouts", tags=["workouts"])


async def update_streak(user_id: int, workout_date: date, db: AsyncSession):
    """Update user streak when a workout is completed."""
    streak_result = await db.execute(select(Streak).where(Streak.user_id == user_id))
    streak = streak_result.scalar_one_or_none()
    
    if not streak:
        streak = Streak(user_id=user_id, current_streak=1, longest_streak=1, last_workout_date=workout_date)
        db.add(streak)
    else:
        # Check if workout is consecutive day
        if streak.last_workout_date:
            days_diff = (workout_date - streak.last_workout_date).days
            if days_diff == 1:
                streak.current_streak += 1
                if streak.current_streak > streak.longest_streak:
                    streak.longest_streak = streak.current_streak
            elif days_diff > 1:
                streak.current_streak = 1
        else:
            streak.current_streak = 1
        streak.last_workout_date = workout_date
    
    await db.commit()


async def check_personal_records(user_id: int, exercise_name: str, weight_kg: float, reps: int, workout_date: date, db: AsyncSession):
    """Check and update personal records for an exercise."""
    pr_result = await db.execute(
        select(PersonalRecord).where(
            PersonalRecord.user_id == user_id,
            PersonalRecord.exercise_name == exercise_name
        )
    )
    pr = pr_result.scalar_one_or_none()
    
    if not pr:
        pr = PersonalRecord(
            user_id=user_id,
            exercise_name=exercise_name,
            best_weight_kg=weight_kg,
            best_reps=reps,
            best_weight_date=workout_date,
            best_reps_date=workout_date
        )
        db.add(pr)
    else:
        updated = False
        if weight_kg and (not pr.best_weight_kg or weight_kg > pr.best_weight_kg):
            pr.best_weight_kg = weight_kg
            pr.best_weight_date = workout_date
            updated = True
        if reps and (not pr.best_reps or reps > pr.best_reps):
            pr.best_reps = reps
            pr.best_reps_date = workout_date
            updated = True
        if updated:
            await db.commit()


async def create_activity_log(user_id: int, activity_type: str, title: str, description: str, meta_data: dict, db: AsyncSession):
    """Create an activity log entry for the timeline."""
    activity = ActivityLog(
        user_id=user_id,
        activity_type=activity_type,
        title=title,
        description=description,
        meta_data=meta_data,
        date=date.today()
    )
    db.add(activity)
    await db.commit()


async def _mark_pool_slot_done(user_id: int, slot_key: str | None, db: AsyncSession):
    """If slot_key is given, flip the matching weekly-plan pool item to done."""
    if not slot_key:
        return
    from app.services.plan_service import mark_slot_done
    result = await db.execute(select(WeeklyPlan).where(WeeklyPlan.user_id == user_id))
    plan_row = result.scalar_one_or_none()
    if not plan_row:
        return
    plan_row.plan = mark_slot_done(plan_row.plan, slot_key)
    await db.commit()


# ── Workout logging ────────────────────────────────────────────────────────────

@router.post("/log", response_model=WorkoutResponse, status_code=201)
async def log_workout(
    body: WorkoutLogRequest,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    log_date = body.date or date.today()
    
    # Calculate analytics data
    total_sets = 0
    total_reps = 0
    calories_estimate = None
    
    if body.exercises:
        for exercise in body.exercises:
            if exercise.get("sets"):
                total_sets += len(exercise["sets"])
                for set_data in exercise["sets"]:
                    total_reps += _safe_int(set_data.get("reps"))
    
    # Estimate calories: ~5-8 calories per minute based on intensity
    if body.duration:
        calories_estimate = round(body.duration * 6.5)
    
    workout = Workout(
        user_id=current_user.id,
        date=log_date,
        muscle_group=body.muscle_group,
        exercises=body.exercises if body.exercises else None,
        exercises_done=body.exercises_done,
        duration=body.duration,
        completed=True,
        mode=body.mode,
        sport=body.sport,
        zone=body.zone,
        notes=body.notes,
        total_sets=total_sets if total_sets > 0 else None,
        total_reps=total_reps if total_reps > 0 else None,
        calories_estimate=calories_estimate,
        completion_percentage=100.0,
    )
    db.add(workout)
    await db.commit()
    await db.refresh(workout)

    # Update streak
    await update_streak(current_user.id, log_date, db)
    
    # Check personal records for exercises with weight/reps
    if body.exercises:
        for exercise in body.exercises:
            exercise_name = exercise.get("name")
            if exercise.get("sets"):
                for set_data in exercise["sets"]:
                    # Accept both keys — the ghost-trainer session sends
                    # "weight" (see saveWorkoutSession() in ghost-trainer.js),
                    # not "weight_kg", so that lookup was always silently 0.
                    weight = set_data.get("weight_kg", set_data.get("weight"))
                    reps = _safe_int(set_data.get("reps"))
                    weight = _safe_int(weight) if not isinstance(weight, (int, float)) else weight
                    if weight or reps:
                        await check_personal_records(
                            current_user.id,
                            exercise_name,
                            weight or 0,
                            reps or 0,
                            log_date,
                            db
                        )
    
    # Create activity log
    await create_activity_log(
        current_user.id,
        "workout",
        f"Completed {body.muscle_group or 'Workout'}",
        f"Duration: {body.duration} min",
        {"duration": body.duration, "muscle_group": body.muscle_group},
        db
    )

    total_result = await db.execute(
        select(sqlfunc.count()).where(Workout.user_id == current_user.id, Workout.completed == True)
    )
    await check_and_award_badges(current_user.id, total_result.scalar() or 0, db)
    await _mark_pool_slot_done(current_user.id, body.slot_key, db)
    return workout


@router.post("/finish")
async def finish_workout(
    body: WorkoutFinishRequest,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """Log a completed Ghost Trainer session from the mobile app."""
    workout_date = date.today()
    
    # Estimate calories
    calories_estimate = round(body.duration_minutes * 6.5) if body.duration_minutes else None
    
    workout = Workout(
        user_id=current_user.id,
        date=workout_date,
        muscle_group=body.muscle_group or "Mixed",
        exercises_done=", ".join(body.exercises_done) if body.exercises_done else None,
        duration=body.duration_minutes,
        completed=True,
        zone=body.zone or "green",
        notes=body.notes,
        calories_estimate=calories_estimate,
        completion_percentage=100.0,
    )
    db.add(workout)
    await db.commit()
    await db.refresh(workout)

    # Update streak
    await update_streak(current_user.id, workout_date, db)
    
    # Create activity log
    await create_activity_log(
        current_user.id,
        "workout",
        f"Completed {body.muscle_group or 'Workout'}",
        f"Duration: {body.duration_minutes} min",
        {"duration": body.duration_minutes, "muscle_group": body.muscle_group},
        db
    )

    total_result = await db.execute(
        select(sqlfunc.count()).where(Workout.user_id == current_user.id, Workout.completed == True)
    )
    await check_and_award_badges(current_user.id, total_result.scalar() or 0, db)

    # Award XP: +100 per completed workout
    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()
    if profile:
        profile.xp = (profile.xp or 0) + 100
        await db.commit()

    await _mark_pool_slot_done(current_user.id, body.slot_key, db)

    return {"id": workout.id, "message": "Workout logged successfully", "xp_gained": 100}


# ── History ────────────────────────────────────────────────────────────────────

@router.get("/history", response_model=list[WorkoutResponse])
async def get_workout_history(
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    result = await db.execute(
        select(Workout)
        .where(Workout.user_id == current_user.id, Workout.completed == True)
        .order_by(Workout.date.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/history/{workout_id}")
async def get_workout_detail(
    workout_id: int,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single workout with its per-set logs."""
    result = await db.execute(
        select(Workout).where(Workout.id == workout_id, Workout.user_id == current_user.id)
    )
    workout = result.scalar_one_or_none()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    sets_result = await db.execute(
        select(SetLog)
        .where(SetLog.workout_id == workout_id, SetLog.user_id == current_user.id)
        .order_by(SetLog.exercise_name, SetLog.set_number)
    )
    sets = sets_result.scalars().all()

    return {
        "id": workout.id,
        "date": str(workout.date),
        "muscle_group": workout.muscle_group,
        "duration": workout.duration,
        "zone": workout.zone,
        "notes": workout.notes,
        "exercises_done": workout.exercises_done,
        "sets": [
            {
                "exercise_name": s.exercise_name,
                "set_number": s.set_number,
                "reps": s.reps,
                "weight_kg": s.weight_kg,
                "feedback": s.feedback,
                "is_pr": s.is_pr,
            }
            for s in sets
        ],
    }


# ── Set logging (progressive overload) ────────────────────────────────────────

@router.post("/sets", response_model=SetLogResponse, status_code=201)
async def log_set(
    body: SetLogRequest,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """Log weight/reps for a single set. Auto-detects personal records."""
    log_date = body.date or date.today()

    # Check if this is a PR (heavier than any previous set for this exercise)
    is_pr = False
    if body.weight_kg is not None and body.weight_kg > 0:
        pr_result = await db.execute(
            select(sqlfunc.max(SetLog.weight_kg)).where(
                SetLog.user_id == current_user.id,
                SetLog.exercise_name == body.exercise_name,
                SetLog.date < log_date,
            )
        )
        prev_max = pr_result.scalar()
        if prev_max is None or body.weight_kg > prev_max:
            is_pr = True

    set_log = SetLog(
        user_id=current_user.id,
        workout_id=body.workout_id,
        exercise_name=body.exercise_name,
        set_number=body.set_number,
        reps=body.reps,
        weight_kg=body.weight_kg,
        feedback=body.feedback,
        is_pr=is_pr,
        date=log_date,
    )
    db.add(set_log)

    # Award XP: +10 per set, +50 bonus for PR
    xp_gained = 10 + (50 if is_pr else 0)
    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()
    if profile:
        profile.xp = (profile.xp or 0) + xp_gained

    await db.commit()
    await db.refresh(set_log)
    return set_log


@router.get("/progressive-overload/{exercise_name}", response_model=ProgressiveOverloadResponse)
async def get_progressive_overload(
    exercise_name: str,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """Return last session's weight and a suggested increment for today."""
    # Last session for this exercise (most recent date, heaviest set)
    last_result = await db.execute(
        select(SetLog.weight_kg, SetLog.reps, SetLog.date)
        .where(
            SetLog.user_id == current_user.id,
            SetLog.exercise_name == exercise_name,
            SetLog.weight_kg.isnot(None),
        )
        .order_by(desc(SetLog.date), desc(SetLog.weight_kg))
        .limit(1)
    )
    last = last_result.first()

    # All-time PR
    pr_result = await db.execute(
        select(sqlfunc.max(SetLog.weight_kg)).where(
            SetLog.user_id == current_user.id,
            SetLog.exercise_name == exercise_name,
        )
    )
    pr_weight = pr_result.scalar()

    if not last:
        return ProgressiveOverloadResponse(
            exercise_name=exercise_name,
            last_weight_kg=None,
            suggested_weight_kg=None,
            last_reps=None,
            last_session_date=None,
            pr_weight_kg=pr_weight,
            message="First time doing this exercise — start light and nail the form.",
        )

    last_weight, last_reps, last_date = last

    # Adaptive increment: read recent feedback (last 10 sets) to adjust
    feedback_result = await db.execute(
        select(SetLog.feedback)
        .where(
            SetLog.user_id == current_user.id,
            SetLog.exercise_name == exercise_name,
            SetLog.feedback.isnot(None),
        )
        .order_by(desc(SetLog.date))
        .limit(10)
    )
    feedbacks = [r[0] for r in feedback_result.all()]
    easy_count = feedbacks.count("easy")
    hard_count = feedbacks.count("hard")
    total_fb = len(feedbacks)

    base_increment = 2.5 if (last_weight or 0) >= 20 else 1.25
    if total_fb >= 3:
        easy_ratio = easy_count / total_fb
        hard_ratio = hard_count / total_fb
        if easy_ratio >= 0.6:
            # Consistently easy → bigger jump
            increment = base_increment * 2
            adaptive_note = "You've been breezing through this — time to push harder!"
        elif hard_ratio >= 0.6:
            # Consistently hard → hold weight, focus form
            increment = 0
            adaptive_note = "This has been challenging — lock in perfect form before adding weight."
        else:
            increment = base_increment
            adaptive_note = ""
    else:
        increment = base_increment
        adaptive_note = ""

    suggested = round((last_weight or 0) + increment, 2)
    days_ago = (date.today() - last_date).days
    age_str = "today" if days_ago == 0 else f"{days_ago}d ago"
    base_msg = f"Last session ({age_str}): {last_weight}kg × {last_reps} reps → try {suggested}kg today."
    message = f"{base_msg} {adaptive_note}".strip()

    return ProgressiveOverloadResponse(
        exercise_name=exercise_name,
        last_weight_kg=last_weight,
        suggested_weight_kg=suggested,
        last_reps=last_reps,
        last_session_date=str(last_date),
        pr_weight_kg=pr_weight,
        message=message,
    )


# ── Exercise swap ──────────────────────────────────────────────────────────────

@router.post("/swap-exercise")
async def swap_exercise(
    body: ExerciseSwapRequest,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """Return an alternative exercise for the current slot."""
    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from app.services.plan_service import get_exercises_for_slot
    # Fetch a fresh set of exercises for the slot
    exercises = get_exercises_for_slot(body.slot_key, profile, body.zone)
    # Filter out the exercise being swapped
    alternatives = [e for e in exercises if e.get("name") != body.exercise_name]

    if not alternatives:
        raise HTTPException(status_code=404, detail="No alternative exercises available")

    # Return a random alternative
    return {"exercise": random.choice(alternatives)}


# ── Streak ────────────────────────────────────────────────────────────────────

@router.get("/streak")
async def get_streak(
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    from app.routers.progress import _calculate_streak
    streak = await _calculate_streak(current_user.id, db)
    return {"streak": streak}


# ── Weekly plan ───────────────────────────────────────────────────────────────

@router.get("/weekly-plan")
async def get_weekly_plan(
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.plan_service import generate_weekly_plan, maybe_reset_week

    result = await db.execute(select(WeeklyPlan).where(WeeklyPlan.user_id == current_user.id))
    plan = result.scalar_one_or_none()

    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()

    # Self-heal: same as the Coach entrypoint — don't wall an existing user
    # with real profile data back into onboarding just because this flag was
    # never flipped.
    if profile and not profile.onboarding_complete:
        from app.services.plan_service import profile_has_usable_data
        if profile_has_usable_data(profile):
            profile.onboarding_complete = True
            await db.commit()

    if not plan:
        if not profile:
            raise HTTPException(status_code=400, detail="Complete onboarding first")

        # Don't gate plan generation on the onboarding_complete flag — an
        # existing user may have a usable profile (goal, days_per_week, etc.)
        # without that specific flag being set. generate_weekly_plan() already
        # defaults any missing fields sensibly (general_fitness / 4 days / gym),
        # so just build a best-effort plan as if this were day one.
        plan_data = generate_weekly_plan(profile)
        plan = WeeklyPlan(user_id=current_user.id, plan=plan_data, mode=profile.active_mode)
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
    elif profile:
        # Roll into a fresh pool if we've crossed into a new week
        reset_plan = maybe_reset_week(plan.plan, profile)
        if reset_plan is not plan.plan:
            plan.plan = reset_plan
            await db.commit()

    return {"plan": plan.plan, "mode": plan.mode, "updated_at": str(plan.updated_at)}


@router.post("/weekly-plan/refresh")
async def refresh_weekly_plan(
    body: RegeneratePlanRequest = RegeneratePlanRequest(),
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """Force-regenerate the weekly plan pool (e.g. after profile changes),
    preserving 'done' status for any slot type that still exists in the new
    pool. Optionally updates profile.goal first — the template lookup in
    plan_service is keyed on (gender, mode, goal), so a new goal (with the
    same on-file gender) genuinely produces a different pool, not just a
    reshuffle. This only ever touches the profile row and the WeeklyPlan's
    JSON pool — past Workout/Streak/PersonalRecord rows are never touched,
    so workout history and streaks survive a regenerate untouched."""
    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if body.goal:
        profile.goal = body.goal
        await db.commit()
        await db.refresh(profile)

    from app.services.plan_service import build_weekly_pool, generate_weekly_plan

    result = await db.execute(select(WeeklyPlan).where(WeeklyPlan.user_id == current_user.id))
    plan = result.scalar_one_or_none()

    new_pool = build_weekly_pool(profile)
    if plan:
        done_keys = {item["key"] for item in plan.plan.get("pool", []) if item.get("done")}
        for item in new_pool:
            if item["key"] in done_keys:
                item["done"] = True
        # goal/level/days_per_week are cached alongside the pool at plan-
        # generation time — a partial rebuild here only touched pool/mode
        # before, leaving plan.plan["goal"] stale (still the old goal) even
        # though the pool itself was correctly rebuilt from the new one.
        plan.plan = {
            **plan.plan,
            "pool": new_pool,
            "mode": profile.active_mode,
            "goal": profile.goal,
        }
        plan.mode = profile.active_mode
    else:
        plan_data = generate_weekly_plan(profile)
        plan = WeeklyPlan(user_id=current_user.id, plan=plan_data, mode=profile.active_mode)
        db.add(plan)

    await db.commit()
    return {"plan": plan.plan, "mode": profile.active_mode}


@router.post("/weekly-plan/select")
async def select_weekly_plan_slot(
    body: SlotSelectRequest,
    zone: str = "green",
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """Pick a session type to train right now — swaps it into the pool (in place of
    the first still-undone slot) if it isn't already part of this week's split,
    and returns its exercises. Does not mark anything done — that happens on finish."""
    from app.services.plan_service import select_pool_slot, get_slot, build_full_session

    result = await db.execute(select(WeeklyPlan).where(WeeklyPlan.user_id == current_user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="No weekly plan found — open the Planner tab first")

    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    plan.plan = select_pool_slot(plan.plan, body.slot_key)
    await db.commit()

    slot = get_slot(plan.plan, body.slot_key)
    exercises = build_full_session(slot, profile, zone)
    return {"plan": plan.plan, "slot": slot, "exercises": exercises}


# ── Today's exercises ─────────────────────────────────────────────────────────

@router.get("/todays-exercises")
async def get_todays_exercises(
    slot_key: str,
    zone: str = "green",
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from app.services.plan_service import get_exercises_for_slot
    exercises = get_exercises_for_slot(slot_key, profile, zone)
    return {"exercises": exercises, "zone": zone, "slot_key": slot_key}


@router.get("/exercise-library")
async def get_exercise_library(
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """All exercises available to this user's profile, grouped by session category —
    powers the Ghost Trainer's free-practice browser. Reuses the same rich catalog
    (with movement_pattern tags, for pose analysis) as the AI weekly planner,
    rather than the separate (unseeded) `exercises` SQL table used by GET /exercises."""
    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from app.services.plan_service import get_exercises_for_slot, SESSION_LABELS, _SESSION_MAPS, _MALE_HOME_MAP, _SPORT

    gender = (profile.gender or "male").lower()
    if gender not in ("male", "female"):
        gender = "male"
    mode = profile.active_mode

    if mode == "sport" and profile.sport:
        keys = list(_SPORT.get((profile.sport or "").lower(), {}).keys())
    else:
        sess_map = _SESSION_MAPS.get((gender, mode), _MALE_HOME_MAP)
        keys = sorted(set(sess_map.values()))

    library: dict[str, list] = {}
    for key in keys:
        exercises = get_exercises_for_slot(key, profile, "green")
        if exercises:
            library[key] = exercises

    return {
        "library": library,
        "labels": {k: SESSION_LABELS.get(k, k.replace("_", " ").title()) for k in library},
    }


# ── Exercise library ──────────────────────────────────────────────────────────

@router.get("/exercises")
async def get_exercises(
    category: str | None = None,
    gender: str | None = None,
    mode: str | None = None,
    sport: str | None = None,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Exercise).where(Exercise.is_active == True)
    if category:
        query = query.where(Exercise.category == category)
    if gender:
        query = query.where(Exercise.gender.in_([gender, "any"]))
    if mode:
        query = query.where(Exercise.mode.in_([mode, "any"]))
    if sport:
        query = query.where(Exercise.sport == sport)

    result = await db.execute(query.limit(100))
    return [
        {
            "id": e.id, "name": e.name, "category": e.category,
            "sets": e.sets, "reps": e.reps, "rest": e.rest,
            "muscle": e.muscle, "weight_guide": e.weight_guide,
            "equipment_required": e.equipment_required, "demo_url": e.demo_url,
        }
        for e in result.scalars().all()
    ]


# ── FCM Token registration ─────────────────────────────────────────────────────

@router.post("/fcm-token", status_code=201)
async def register_fcm_token(
    body: FCMTokenRequest,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """Register or refresh a device FCM token for push notifications."""
    # Upsert: deactivate old tokens for this user, then insert new one
    existing_result = await db.execute(
        select(FCMToken).where(
            FCMToken.user_id == current_user.id,
            FCMToken.token == body.token,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.is_active = True
        existing.platform = body.platform
    else:
        fcm = FCMToken(
            user_id=current_user.id,
            token=body.token,
            platform=body.platform,
            is_active=True,
        )
        db.add(fcm)

    await db.commit()
    return {"message": "FCM token registered"}
