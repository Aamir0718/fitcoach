"""
All AI logic — Groq calls, prompt building, intent classification, onboarding flow.
Completely separated from routing.
"""
import re
import json
import asyncio
import logging
import io
from datetime import datetime
from typing import Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from groq import AsyncGroq
from app.services.food_detector import detect_foods
from app.services.nutrition_service import get_food_nutrition
from app.config import settings
from app.models.profile import Profile
from app.models.workout import AIMemory, WeeklyPlan, PlannedWorkout, Exercise
from app.schemas.workout import ChatResponse
from app.services.plan_service import (
    generate_weekly_plan, get_todays_slot, get_exercises_for_slot,
    swap_today_slot, MUSCLE_TO_SLOT, SESSION_LABELS,
)

logger = logging.getLogger(__name__)
_groq = AsyncGroq(api_key=settings.GROQ_API_KEY)

# ── Injection guard ────────────────────────────────────────────────────────────
_INJECTION_PATTERNS = [
    "ignore previous", "ignore all", "disregard", "forget instructions",
    "you are now", "act as", "jailbreak", "new persona", "pretend you",
    "system prompt", "override", "bypass", "ignore your training",
]

def _sanitize(msg: str) -> str:
    msg = msg[:600].strip()
    lower = msg.lower()
    for p in _INJECTION_PATTERNS:
        if p in lower:
            return "[Message filtered]"
    return msg


# ── Intent classification ──────────────────────────────────────────────────────
_INTENT_MAP = {
    "start_workout": [
        "start", "begin", "let's go", "lets go", "start workout", "begin workout",
        "i'm ready", "im ready", "ready to train", "ready to workout",
    ],
    "next_set": [
        "next", "done", "next set", "done set", "finished set", "ok next",
        "completed", "set done", "i finished",
    ],
    "done_workout": [
        "done workout", "finish workout", "end workout", "log workout",
        "workout done", "complete workout", "i'm done", "im done",
        "that's all", "thats all", "finished workout",
    ],
    "easy": [
        "too easy", "felt easy", "way too easy", "that was easy", "very easy",
    ],
    "hard": [
        "too hard", "felt hard", "that was hard", "too heavy", "couldn't finish",
        "very hard", "i struggled",
    ],
    "show_plan": [
        "my plan", "today's workout", "today workout", "what's today", "show plan",
        "weekly plan", "what do i do", "what should i train", "what workout",
        "what's my workout", "whats my workout", "tell me my workout",
    ],
    "swap_muscle": [
        "i want to do", "i want to train", "i want to work", "skip", "instead",
        "change to", "switch to", "do legs", "do chest", "do back", "do arms",
        "do shoulders", "no i want", "change today", "train legs", "train chest",
        "train back", "train arms", "train shoulders", "train glutes",
        "actually", "let me do", "can i do", "i'd rather do", "id rather do",
        "not chest", "not legs", "not back", "no chest", "no legs",
    ],
    "greeting": [
        "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
        "what's up", "sup", "hiya",
    ],
}

def classify_intent(message: str) -> str:
    lower = message.lower().strip()
    for intent, keywords in _INTENT_MAP.items():
        if any(k in lower for k in keywords):
            return intent
    return "chat"


def _extract_target_muscle(message: str) -> str | None:
    """Parse which muscle group / session the user wants from a swap request."""
    lower = message.lower()
    # Longest match first so "full body" beats "body"
    for phrase in sorted(MUSCLE_TO_SLOT.keys(), key=len, reverse=True):
        if phrase in lower:
            return MUSCLE_TO_SLOT[phrase]
    return None


# ── AI call wrapper ────────────────────────────────────────────────────────────
async def _ai(messages: list[dict], temperature: float = 0.7, max_tokens: int = 400, use_vision: bool = False) -> Tuple[str, str]:
    """
    Call Groq API and return (response, error_type).
    error_type values: "none", "timeout", "rate_limit", "auth_error", "api_error", "json_error"
    use_vision: if True, use vision-capable model for image analysis
    """
    try:
        model = settings.GROQ_VISION_MODEL if use_vision else settings.GROQ_MODEL
        logger.info(f"Calling Groq API with model={model}, messages={len(messages)}, max_tokens={max_tokens}, use_vision={use_vision}")
        resp = await asyncio.wait_for(
            _groq.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ),
            timeout=15,  # Longer timeout for vision analysis
        )
        content = resp.choices[0].message.content.strip()
        logger.info(f"Groq API response received: {len(content)} chars")
        return content, "none"
    except asyncio.TimeoutError:
        logger.warning("Groq API timeout")
        return "", "timeout"
    except Exception as e:
        err = str(e)
        logger.error(f"Groq API error: {err}", exc_info=True)
        
        if "429" in err or "rate_limit" in err.lower():
            return "I'm getting a lot of requests right now — give me a few seconds and try again!", "rate_limit"
        if "401" in err or "403" in err or "authentication" in err.lower():
            return "AI configuration error. Please contact support.", "auth_error"
        if "json" in err.lower() or "parse" in err.lower():
            return "AI response format error. Please try again.", "json_error"
        return "I'm having a moment — try again in a few seconds.", "api_error"


# ── Onboarding ────────────────────────────────────────────────────────────────
ONBOARDING_FIELDS = [
    "name", "date_of_birth", "gender", "height", "weight",
    "goal", "level", "workout_place", "days_per_week", "injuries",
]

ONBOARDING_QUESTIONS = {
    "name":          {"reply": "Hey! Welcome to FitCoach 💪 What's your name?", "input_type": "text"},
    "date_of_birth": {"reply": "Great to meet you, {name}! What's your date of birth?", "input_type": "date"},
    "gender":        {"reply": "Are you male or female?", "input_type": "choice", "options": ["Male", "Female"]},
    "height":        {"reply": "What's your height in cm?", "input_type": "number"},
    "weight":        {"reply": "What's your current weight in kg?", "input_type": "number"},
    "goal":          {"reply": "What's your primary fitness goal?", "input_type": "choice",
                      "options": ["Fat Loss", "Muscle Gain", "Strength", "General Fitness", "Toned Body", "Glute Growth", "Lean Physique", "Hourglass Figure"]},
    "level":         {"reply": "What's your experience level?", "input_type": "choice",
                      "options": ["Beginner", "Intermediate", "Advanced"]},
    "workout_place": {"reply": "Where do you usually train?", "input_type": "choice", "options": ["Gym", "Home"]},
    "days_per_week": {"reply": "How many days per week can you train?", "input_type": "choice",
                      "options": ["3", "4", "5", "6"]},
    "injuries":      {"reply": "Any injuries or areas to avoid? (Type 'none' if healthy)", "input_type": "text"},
    "plays_sport":   {"reply": "Do you play any sport? (Cricket, Football, Running?)", "input_type": "choice", "options": ["Yes", "No"]},
}


async def handle_onboarding_message(
    user_id: int, message: str, profile: Profile, db: AsyncSession
) -> ChatResponse:
    from datetime import date

    msg = message.strip()
    current_field = next(
        (f for f in ONBOARDING_FIELDS if getattr(profile, f) is None),
        None
    )

    if not msg:
        q = ONBOARDING_QUESTIONS.get(current_field or "name")
        reply_text = q["reply"].format(name=profile.name or "")
        return ChatResponse(
            reply=reply_text,
            type="onboarding",
            data={
                "field": current_field,
                "input_type": q.get("input_type", "text"),
                "options": q.get("options"),
                "gender": profile.gender or "",
            }
        )

    # Process current field
    if current_field == "name":
        profile.name = msg.strip().title()
    elif current_field == "date_of_birth":
        profile.date_of_birth = msg
        try:
            dob = date.fromisoformat(msg)
            today = date.today()
            profile.age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        except ValueError:
            pass
    elif current_field == "gender":
        profile.gender = "male" if msg.lower().startswith("m") else "female"
    elif current_field == "height":
        try:
            profile.height = float(re.sub(r"[^\d.]", "", msg))
        except ValueError:
            pass
    elif current_field == "weight":
        try:
            profile.weight = float(re.sub(r"[^\d.]", "", msg))
        except ValueError:
            pass
    elif current_field == "goal":
        goal_map = {
            "fat loss": "fat_loss", "muscle gain": "muscle_gain", "muscle": "muscle_gain",
            "strength": "strength", "general": "general_fitness", "fitness": "general_fitness",
            "toned": "toned_body", "glute": "glute_growth", "lean": "lean_physique",
            "hourglass": "hourglass_figure",
        }
        lower = msg.lower()
        profile.goal = next((v for k, v in goal_map.items() if k in lower), "general_fitness")
    elif current_field == "level":
        lower = msg.lower()
        profile.level = "advanced" if "adv" in lower else ("intermediate" if "int" in lower else "beginner")
    elif current_field == "workout_place":
        profile.workout_place = "home" if "home" in msg.lower() else "gym"
    elif current_field == "days_per_week":
        try:
            profile.days_per_week = int(re.sub(r"[^\d]", "", msg)) or 4
        except ValueError:
            profile.days_per_week = 4
    elif current_field == "injuries":
        profile.injuries = msg if msg.lower() not in ("none", "no", "n/a", "-") else "none"

    # Advance to next field
    next_field = next(
        (f for f in ONBOARDING_FIELDS if getattr(profile, f) is None),
        None
    )

    if next_field is None:
        # Ask about sport
        if profile.plays_sport is None:
            profile.plays_sport = False  # default
            await db.commit()
            return ChatResponse(
                reply="Do you play any sport? (Cricket, Football, Running, or other)",
                type="onboarding",
                data={"field": "plays_sport", "input_type": "choice", "options": ["Yes", "No"]}
            )
        # Onboarding complete
        profile.onboarding_complete = True
        await db.commit()

        # Generate weekly plan
        plan_data = generate_weekly_plan(profile)
        plan = WeeklyPlan(user_id=user_id, plan=plan_data, mode=profile.active_mode)
        db.add(plan)
        await db.commit()

        today_slot = get_todays_slot(plan_data)
        muscle = today_slot.get("label", "Full Body") if today_slot else "Full Body"

        return ChatResponse(
            reply=f"You're all set, {profile.name}! 🎉\n\nYour personalised plan is ready. Today's focus: **{muscle}**\n\nSay 'start' when you're ready to begin!",
            type="onboarding_complete",
            data={"plan": plan_data, "today": today_slot}
        )

    await db.commit()
    q = ONBOARDING_QUESTIONS.get(next_field, ONBOARDING_QUESTIONS["name"])
    reply_text = q["reply"].format(name=profile.name or "")
    return ChatResponse(
        reply=reply_text,
        type="onboarding",
        data={
            "field": next_field,
            "input_type": q.get("input_type", "text"),
            "options": q.get("options"),
        }
    )


# ── Workout commands ───────────────────────────────────────────────────────────
# In-memory workout session state
_workout_sessions: dict[int, dict] = {}


async def handle_workout_command(
    user_id: int, message: str, intent: str, profile: Profile,
    zone: str, mode: str, db: AsyncSession
) -> ChatResponse:

    # ── Check sport onboarding ────────────────────────────────────────────────
    if profile.active_mode == "sport" and not profile.sport_onboarding_complete:
        return ChatResponse(
            reply=(
                f"You're set to Sports Mode but haven't completed your sport profile yet, {profile.name}! 🏏\n\n"
                "Go to **Profile → Sports Setup** to tell me which sport you play, your role, and match frequency.\n\n"
                "I'll then create a sport-specific training plan that actually makes you better on the field!"
            ),
            type="sport_onboarding_required",
            data={}
        )

    # ── Greeting / show plan ──────────────────────────────────────────────────
    if intent in ("show_plan", "greeting"):
        return await _build_greeting(user_id, profile, zone, db)

    # ── Muscle group swap ─────────────────────────────────────────────────────
    if intent == "swap_muscle":
        return await _handle_swap(user_id, message, profile, zone, db)

    # ── Start workout ─────────────────────────────────────────────────────────
    if intent == "start_workout":
        return await _start_workout(user_id, profile, zone, mode, db)

    # ── Next set ──────────────────────────────────────────────────────────────
    if intent == "next_set" and user_id in _workout_sessions:
        return _next_set(user_id, profile.gender or "male")

    # ── Done workout ──────────────────────────────────────────────────────────
    if intent == "done_workout":
        return await _log_and_finish(user_id, profile, db)

    # ── Feedback ──────────────────────────────────────────────────────────────
    if intent in ("easy", "hard") and user_id in _workout_sessions:
        session = _workout_sessions[user_id]
        mg = session.get("muscle_group", "")
        mem = AIMemory(user_id=user_id, muscle_group=mg, feedback=intent, summary=f"{mg} felt {intent}")
        db.add(mem)
        await db.commit()
        msg = "🔥 Beast mode! I'll push harder next time." if intent == "easy" else "💪 Smart choice. Rest is growth."
        return ChatResponse(reply=f"{msg}\n\nTap **Log Workout** to save.", type="feedback_received")

    return await handle_free_chat(user_id, message, profile, zone, db)


async def _handle_swap(
    user_id: int, message: str, profile: Profile, zone: str, db: AsyncSession
) -> ChatResponse:
    """Handle 'I want to do legs instead' type requests — swaps plan + serves exercises."""
    target_slot = _extract_target_muscle(message)

    if not target_slot:
        # Ask Groq to extract the muscle group
        if settings.GROQ_API_KEY:
            slot_raw, error_type = await _ai([
                {"role": "system", "content": (
                    "Extract the workout type the user wants to do. "
                    "Reply with ONLY one of: push, pull, legs, upper_body, lower_body, "
                    "full_body, cardio, glutes, core_cardio. Nothing else."
                )},
                {"role": "user", "content": message},
            ], temperature=0.1, max_tokens=10)
            if error_type != "none":
                logger.warning(f"Failed to extract muscle group via AI: {error_type}")
                target_slot = "full_body"
            else:
                target_slot = slot_raw.strip().lower().replace(" ", "_")
                # Validate it's a known slot
                if target_slot not in SESSION_LABELS:
                    target_slot = "full_body"
        else:
            target_slot = "full_body"

    # Fetch current plan
    plan_result = await db.execute(select(WeeklyPlan).where(WeeklyPlan.user_id == user_id))
    plan_row = plan_result.scalar_one_or_none()

    if not plan_row:
        plan_data = generate_weekly_plan(profile)
        plan_row = WeeklyPlan(user_id=user_id, plan=plan_data, mode=profile.active_mode)
        db.add(plan_row)
    else:
        plan_data = plan_row.plan

    # Swap today in the plan
    updated_plan = swap_today_slot(plan_data, target_slot)
    plan_row.plan = updated_plan
    await db.commit()

    # Get exercises for new slot
    exercises = get_exercises_for_slot(target_slot, profile, zone)
    label = SESSION_LABELS.get(target_slot, target_slot.replace("_", " ").title())

    if not exercises:
        return ChatResponse(
            reply=f"Switched today to **{label}**! 📅\n\nI've updated your plan. Head to the Workout tab and press Start to begin.",
            type="plan_swapped",
            data={"new_slot": target_slot, "label": label}
        )

    # Start the session immediately with new exercises
    _workout_sessions[user_id] = {
        "exercises": exercises,
        "muscle_group": label,
        "current_index": 0,
        "current_set": 1,
        "start_time": datetime.now().isoformat(),
        "zone": zone,
        "mode": profile.active_mode,
        "completed": [],
    }

    ex = exercises[0]
    intensity = {"green": "Full intensity 💚", "yellow": "Moderate intensity 💛", "red": "Light session 🔴"}[zone]

    ex_lines = "\n".join(
        f"**{i+1}. {e['name']}** — {e['reps']} reps × {e['sets']} sets"
        for i, e in enumerate(exercises[:6])
    )
    if len(exercises) > 6:
        ex_lines += f"\n...and {len(exercises)-6} more"

    reply = (
        f"Switched to **{label}** today! ✅ Plan updated.\n\n"
        f"{intensity}\n\n"
        f"Here's your session:\n{ex_lines}\n\n"
        f"Starting with **{ex['name']}** — say **'next'** after each set, **'done'** when finished!"
    )

    return ChatResponse(
        reply=reply,
        type="workout_start",
        data={
            "muscle_group": label,
            "exercises": exercises,
            "current_exercise": ex,
            "current_exercise_index": 0,
            "current_set": 1,
            "total_exercises": len(exercises),
            "zone": zone,
            "plan_updated": True,
        }
    )


async def _build_greeting(user_id: int, profile: Profile, zone: str, db: AsyncSession) -> ChatResponse:
    plan_result = await db.execute(select(WeeklyPlan).where(WeeklyPlan.user_id == user_id))
    plan_row = plan_result.scalar_one_or_none()

    if not plan_row:
        plan_data = generate_weekly_plan(profile)
        plan_row = WeeklyPlan(user_id=user_id, plan=plan_data, mode=profile.active_mode)
        db.add(plan_row)
        await db.commit()
    else:
        plan_data = plan_row.plan

    today_slot = get_todays_slot(plan_data)
    muscle = today_slot.get("label", "Full Body") if today_slot else "Full Body"
    is_rest = today_slot.get("rest", False) if today_slot else False

    h = datetime.now().hour
    tod = "Morning" if h < 12 else ("Afternoon" if h < 17 else "Evening")
    tod_emoji = "🌅" if h < 12 else ("☀️" if h < 17 else "🌙")

    zone_labels = {
        "green":  "Fully recovered ✅ — Train hard today!",
        "yellow": "Moderate recovery ⚠️ — Keep intensity controlled.",
        "red":    "Low recovery 🔴 — Light session recommended.",
    }

    # Build personalized context
    goal_display = (profile.goal or "general_fitness").replace("_", " ").title()
    mode_display = profile.active_mode.replace("_", " ").title()

    if is_rest:
        reply = (
            f"Good {tod} {tod_emoji}, **{profile.name}**!\n\n"
            f"Today is your **Rest Day** — recovery is where the gains actually happen. 😴\n\n"
            f"Recovery: {zone_labels.get(zone, zone)}\n\n"
            f"Use the time to eat well, sleep enough, and come back stronger tomorrow. "
            f"You can still ask me anything about nutrition, form, or your plan!"
        )
    else:
        # Count remaining exercises
        exercises = get_exercises_for_slot(today_slot, profile, zone) if today_slot else []
        ex_count = len(exercises)

        # Build exercise preview
        ex_preview = ""
        if exercises:
            first_three = exercises[:3]
            ex_preview = "**Today's exercises:** " + " · ".join(e["name"] for e in first_three)
            if ex_count > 3:
                ex_preview += f" · +{ex_count-3} more"
            ex_preview = "\n\n" + ex_preview

        reply = (
            f"Good {tod} {tod_emoji}, **{profile.name}**! 💪\n\n"
            f"**Today: {muscle}** ({mode_display} · {goal_display})\n"
            f"Recovery: {zone_labels.get(zone, zone)}"
            f"{ex_preview}\n\n"
            f"Say **'start'** to begin your session, or tell me if you want to train something different!"
        )

    return ChatResponse(
        reply=reply,
        type="daily_plan",
        data={"today": today_slot, "plan": plan_data, "zone": zone, "muscle": muscle}
    )


async def _start_workout(user_id: int, profile: Profile, zone: str, mode: str, db: AsyncSession) -> ChatResponse:
    plan_result = await db.execute(select(WeeklyPlan).where(WeeklyPlan.user_id == user_id))
    plan_row = plan_result.scalar_one_or_none()
    plan_data = plan_row.plan if plan_row else generate_weekly_plan(profile)

    today_slot = get_todays_slot(plan_data) or {"label": "Full Body", "db_key": "full_body"}
    exercises = get_exercises_for_slot(today_slot, profile, zone)
    muscle_group = today_slot.get("label", "Full Body")

    if today_slot.get("rest"):
        return ChatResponse(
            reply=(
                f"Today is your rest day, {profile.name}! 😴\n\n"
                "Your body needs this to grow and recover. Trust the process.\n\n"
                "If you really want to move, try a 20-minute walk or light stretching — nothing intense. "
                "Say **'start anyway'** if you absolutely want to train."
            ),
            type="rest_day",
            data={"today": today_slot}
        )

    if not exercises:
        exercises = get_exercises_for_slot("full_body", profile, zone)

    _workout_sessions[user_id] = {
        "exercises": exercises,
        "muscle_group": muscle_group,
        "current_index": 0,
        "current_set": 1,
        "start_time": datetime.now().isoformat(),
        "zone": zone,
        "mode": mode,
        "completed": [],
    }

    ex = exercises[0]
    intensity = {"green": "Full intensity 💚", "yellow": "Moderate intensity 💛", "red": "Light session 🔴"}[zone]
    intro = "Lock in. Every rep counts."

    return ChatResponse(
        reply=(
            f"LET'S GO! 🔥 **{muscle_group}** — {intensity}\n\n"
            f"{intro}\n\n"
            f"**{ex['name']}**\n"
            f"{ex.get('weight_guide', 'Bodyweight')} · {ex['reps']} reps · {ex['sets']} sets\n\n"
            f"Say **'next'** after each set, **'done'** when the whole workout is finished!"
        ),
        type="workout_start",
        data={
            "muscle_group": muscle_group,
            "exercises": exercises,
            "current_exercise": ex,
            "current_exercise_index": 0,
            "current_set": 1,
            "total_exercises": len(exercises),
            "zone": zone,
        }
    )


def _next_set(user_id: int, gender: str) -> ChatResponse:
    session = _workout_sessions[user_id]
    ex = session["exercises"][session["current_index"]]
    session["current_set"] += 1

    if session["current_set"] > int(ex.get("sets", 3)):
        session["completed"].append(ex["name"])
        session["current_index"] += 1
        session["current_set"] = 1

        if session["current_index"] >= len(session["exercises"]):
            return ChatResponse(
                reply=(
                    "🎉 **All exercises done!**\n\n"
                    "How did that feel? Say **'easy'**, **'hard'**, or just **'done workout'** to log it!"
                ),
                type="workout_all_done",
                data={}
            )

        next_ex = session["exercises"][session["current_index"]]
        remaining = len(session["exercises"]) - session["current_index"]
        return ChatResponse(
            reply=(
                f"✅ Next: **{next_ex['name']}**\n"
                f"{next_ex.get('weight_guide', 'Bodyweight')} · {next_ex['reps']} reps · {next_ex['sets']} sets\n\n"
                f"*{remaining} exercise{'s' if remaining > 1 else ''} left* — keep pushing! 💪"
            ),
            type="workout_next_exercise",
            data={
                "current_exercise": next_ex,
                "current_exercise_index": session["current_index"],
                "current_set": 1,
                "total_exercises": len(session["exercises"]),
            }
        )

    sets_left = int(ex.get("sets", 3)) - session["current_set"] + 1
    return ChatResponse(
        reply=(
            f"Set {session['current_set']}/{ex['sets']} 💪 **{ex['name']}**\n"
            f"{ex.get('weight_guide', 'Bodyweight')} · {ex['reps']} reps\n\n"
            f"*{sets_left} set{'s' if sets_left > 1 else ''} to go for this exercise*"
        ),
        type="workout_next_set",
        data={
            "current_exercise": ex,
            "current_exercise_index": session["current_index"],
            "current_set": session["current_set"],
            "total_exercises": len(session["exercises"]),
        }
    )


async def _log_and_finish(user_id: int, profile: Profile, db: AsyncSession) -> ChatResponse:
    from datetime import date as date_cls
    from app.models.workout import Workout
    from sqlalchemy import func as sqlfunc
    from app.routers.progress import check_and_award_badges, _calculate_streak

    session = _workout_sessions.pop(user_id, {})
    if not session:
        return ChatResponse(reply="No active workout session found.", type="error")

    start = datetime.fromisoformat(session["start_time"])
    duration = max(1, int((datetime.now() - start).total_seconds() / 60))

    workout = Workout(
        user_id=user_id,
        date=date_cls.today(),
        muscle_group=session["muscle_group"],
        exercises_done=", ".join(session.get("completed", [])),
        duration=duration,
        completed=True,
        mode=session.get("mode", "gym"),
        zone=session.get("zone", "green"),
    )
    db.add(workout)
    await db.commit()

    total_result = await db.execute(
        select(sqlfunc.count()).where(Workout.user_id == user_id, Workout.completed == True)
    )
    total = total_result.scalar() or 0
    new_badge = await check_and_award_badges(user_id, total, db)
    streak = await _calculate_streak(user_id, db)

    # Award XP
    profile_result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    p = profile_result.scalar_one_or_none()
    if p:
        p.xp = (p.xp or 0) + 100
        await db.commit()

    badge_msg = f"\n\n🏅 **New Badge: {new_badge.badge_icon} {new_badge.badge_name}!**" if new_badge else ""
    return ChatResponse(
        reply=(
            f"✅ **Workout logged!** {duration} mins · Streak: {streak} days 🔥"
            f"{badge_msg}\n\n"
            "Rest up, hydrate, and eat your protein! 💪"
        ),
        type="workout_logged",
        data={"duration": duration, "streak": streak, "total": total, "new_badge": new_badge.badge_id if new_badge else None}
    )


async def _set_intro(exercise_name: str, set_num: int, gender: str) -> str:
    if not settings.GROQ_API_KEY:
        intros = [
            "Lock in. Every rep counts. 🔥",
            "You've done this before. Do it again. 💪",
            "Breathe. Focus. Execute. ⚡",
            "This set is yours. Own it. 👑",
            "Controlled, powerful, confident. Let's go!",
        ]
        import hashlib
        idx = int(hashlib.md5(f"{exercise_name}{set_num}".encode()).hexdigest(), 16) % len(intros)
        return intros[idx]
    tone = "powerful and motivating" if gender == "male" else "encouraging and energetic"
    intro, error_type = await _ai([
        {"role": "system", "content": f"You are a fitness coach. Be {tone}. One short sentence only. No hashtags."},
        {"role": "user", "content": f"Set {set_num} of {exercise_name}. Give me a motivational cue."},
    ], temperature=0.9, max_tokens=40)
    if error_type != "none":
        logger.warning(f"Failed to generate intro via AI: {error_type}")
        return "Lock in. Every rep counts."
    return intro


# ── Free chat ──────────────────────────────────────────────────────────────────
async def handle_free_chat(
    user_id: int, message: str, profile: Profile, zone: str, db: AsyncSession
) -> ChatResponse:
    msg = _sanitize(message)

    # Fallback when no GROQ key is configured
    if not settings.GROQ_API_KEY:
        reply = _rule_based_chat(msg, profile, zone)
        return ChatResponse(reply=reply, type="chat")

    memory_result = await db.execute(
        select(AIMemory).where(AIMemory.user_id == user_id).order_by(AIMemory.created_at.desc()).limit(3)
    )
    memories = memory_result.scalars().all()
    memory_context = "; ".join([m.summary for m in memories if m.summary]) if memories else ""

    # Build rich profile context
    injuries_note = f"Injuries to avoid: {profile.injuries}." if profile.injuries and profile.injuries.lower() not in ("none", "no") else "No injuries."
    sport_note = f"Sport: {profile.sport} ({profile.sport_role or 'general'})." if profile.plays_sport and profile.sport else ""
    height_weight = f"{profile.height or '?'}cm, {profile.weight or '?'}kg." if profile.height or profile.weight else ""

    system_prompt = f"""You are FitCoach AI — a friendly, conversational gym coach. Talk like a real person, not a textbook.

User profile:
- Name: {profile.name} | Age: {profile.age or '?'} | Gender: {profile.gender or '?'}
- {height_weight}
- Goal: {(profile.goal or 'general_fitness').replace('_', ' ')}
- Level: {profile.level or 'intermediate'}
- Mode: {profile.active_mode} | Workout place: {profile.workout_place or 'gym'}
- Days/week: {profile.days_per_week or 4}
- {injuries_note} {sport_note}
- Recovery zone today: {zone} (green=train hard, yellow=moderate, red=light/rest)
{f'- Recent training history: {memory_context}' if memory_context else ''}

CRITICAL RESPONSE GUIDELINES:
- Default response: 2-5 short sentences (max 80-120 words)
- Only go longer if user explicitly asks for detailed explanation
- Use bullet points when listing items
- Break into short, readable lines
- Never write huge paragraphs
- Be conversational and friendly like a real coach
- Use their name occasionally to personalize
- End with a follow-up question when appropriate
- Use suitable emojis sparingly (💪🔥🥗🏃😄)
- Practical advice only, no scientific jargon
- Respect injuries — avoid suggesting harmful exercises"""

    reply, error_type = await _ai([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": msg},
    ], temperature=0.7, max_tokens=350)
    if error_type != "none" or not reply:
        logger.warning(f"Free chat AI failed with error: {error_type}, falling back to rule-based")
        reply = _rule_based_chat(msg, profile, zone)

    return ChatResponse(reply=reply, type="chat")


def _rule_based_chat(message: str, profile: Profile, zone: str) -> str:
    """Smart rule-based responses when no GROQ API key is configured."""
    lower = message.lower()
    name  = profile.name or "there"
    goal  = profile.goal or "general_fitness"
    level = profile.level or "beginner"
    place = profile.workout_place or "gym"

    zone_msg = {
        "green":  "Your recovery is great — train hard today! 💚",
        "yellow": "Moderate recovery — keep intensity controlled. 💛",
        "red":    "Low recovery — today should be light or a rest day. 🔴",
    }.get(zone, "")

    if any(w in lower for w in ["hello", "hi", "hey"]):
        return f"Hey {name}! 💪 Ready to crush it?\n\n{zone_msg}\n\nAsk me about your workout, nutrition, or how to hit your {goal.replace('_', ' ')} goal faster!"

    if any(w in lower for w in ["motivation", "inspire"]):
        msgs = {
            "fat_loss":    "Every workout burns fat. Every skipped meal choice matters. You're reshaping your body one decision at a time. 🔥",
            "muscle_gain": "Muscles grow when you're consistent, not when you're perfect. Show up, lift heavy, eat right, sleep well. 💪",
            "strength":    "Strength is built through progressive overload and patience. Trust the process — you're getting stronger every session. ⚡",
        }
        return msgs.get(goal, f"You chose this path for a reason, {name}. Every rep is building the version of you that you want to be. Keep going. 🌟")

    if any(w in lower for w in ["protein", "eat", "food", "diet", "nutrition", "meal"]):
        w = profile.weight or 75
        target = round(w * (2.2 if goal == "muscle_gain" else 1.8))
        return f"For {goal.replace('_', ' ')}, aim for **{target}g protein/day** ({round(target/3)}g per meal).\n\nBest sources: chicken breast, eggs, Greek yogurt, tuna, cottage cheese.\n\nDrink at least {round(w * 0.033, 1)}L water daily. 💧"

    if any(w in lower for w in ["rest", "recover", "sleep", "sore"]):
        return f"Recovery IS training, {name}. 🌙\n\n• Sleep 7–9 hours — this is when muscle grows\n• Eat enough protein to rebuild\n• Light walks on rest days keep blood flowing\n• {zone_msg}"

    if any(w in lower for w in ["plan", "schedule", "week", "today", "workout"]):
        return f"Your {level} **{place}** plan is built for **{goal.replace('_', ' ')}** with {profile.days_per_week or 4} days/week.\n\n{zone_msg}\n\nGo to the Workout tab to start your session! Your plan adapts to your recovery scores. 📅"

    return f"Great question, {name}! 🤖\n\n{zone_msg}\n\nUse the Workout tab to start today's personalised session!"


# ── Nutrition analysis (YOLOv8 + USDA) ───────────────────────────────────────────
async def analyze_food_ai(food_description: str = "", image_base64: str | None = None) -> dict:
    """
    Analyze food image using YOLOv8 for detection and USDA for nutrition data.

    Args:
        image_base64: Base64-encoded image string`
        
    Returns:
        Nutrition analysis JSON with detected foods and USDA nutrition data
    """
    import base64
    from app.services.food_detector import detect_foods
    from app.services.nutrition_service import get_food_nutrition
    
    logger.info("Received image for nutrition analysis")
    if not image_base64:
        nutrition = get_food_nutrition(food_description)

        if nutrition is None:
            return {"error": "Food not found"}

        return {
            "meal_name": nutrition["name"],
            "foods": [nutrition],
            "total_calories": nutrition["calories"],
            "total_protein": nutrition["protein"],
            "total_carbs": nutrition["carbs"],
            "total_fat": nutrition["fat"],
            "health_score": 80,
            "tips": [
                "Drink enough water 💧",
                "Eat a balanced diet 🥗"
            ]
        }

    try:
        image_data = base64.b64decode(image_base64)
        import os
        os.makedirs("uploads", exist_ok=True)
        image_path = "uploads/temp.jpg"
        with open(image_path, "wb") as f:
            f.write(image_data)

        logger.info(f"Saved image to {image_path}")

        # Detect foods
        detected_foods = detect_foods(image_path)
        
        if not detected_foods:
            logger.warning("No recognizable food detected")
            return {
                "error": "No recognizable food detected."
            }
        
        logger.info(f"YOLO detected: {detected_foods}")
        
        # Get nutrition data from USDA
        # Get nutrition from USDA
        nutrition_data = []
        for food in detected_foods:
            nutrition = get_food_nutrition(food)
            if nutrition:
                nutrition_data.append(nutrition)
        logger.info(f"USDA nutrition data: {nutrition_data}")
        
        # Calculate totals
        total_calories = sum(f.get("calories", 0) for f in nutrition_data)
        total_protein = sum(f.get("protein", 0) for f in nutrition_data)
        total_carbs = sum(f.get("carbs", 0) for f in nutrition_data)
        total_fat = sum(f.get("fat", 0) for f in nutrition_data)
        
        # Calculate health score and tips
        health_score = 80
        tips = [
            "Drink enough water 💧",
            "Add vegetables for a balanced meal 🥗",
            "Include a good protein source 💪"
        ]
        
        # Generate meal name from detected foods
        meal_name = ", ".join(detected_foods)
        
        # Build response
        foods_response = []
        foods_response.append({
            "name": nutrition["name"],
            "quantity": nutrition["quantity"],
            "calories": nutrition["calories"],
            "protein": nutrition["protein"],
            "carbs": nutrition["carbs"],
            "fat": nutrition["fat"],
            "fiber": nutrition["fiber"],
            "sugar": nutrition["sugar"]
        })
        
        result = {
            "meal_name": meal_name,
            "foods": foods_response,
            "total_calories": total_calories,
            "total_protein": total_protein,
            "total_carbs": total_carbs,
            "total_fat": total_fat,
            "total_fiber": sum(f["fiber"] for f in nutrition_data),
            "total_sugar": sum(f["sugar"] for f in nutrition_data),
            "health_score": health_score,
            "tips": tips
        }
        
        logger.info(f"Final nutrition result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Nutrition analysis failed: {e}", exc_info=True)
        return {
            "error": f"Nutrition analysis failed: {str(e)}"
        }
