"""
All AI logic — Groq calls, prompt building, intent classification, onboarding flow.
Completely separated from routing.
"""
import re
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from groq import AsyncGroq

from app.config import settings
from app.models.profile import Profile
from app.models.workout import AIMemory, WeeklyPlan, PlannedWorkout, Exercise
from app.schemas.workout import ChatResponse
from app.services.plan_service import generate_weekly_plan, get_todays_slot

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
    "start_workout": ["start", "begin", "let's go", "lets go", "start workout", "begin workout", "go"],
    "next_set":      ["next", "done", "next set", "done set", "finished set", "ok next", "..."],
    "done_workout":  ["done workout", "finish", "end workout", "log workout", "workout done", "complete"],
    "easy":          ["easy", "too easy", "felt easy", "way too easy"],
    "hard":          ["hard", "too hard", "felt hard", "tough"],
    "show_plan":     ["my plan", "today's workout", "what's today", "show plan", "weekly plan", "what do i do"],
    "swap":          ["skip", "swap", "switch", "change", "instead of", "replace"],
    "greeting":      ["hi", "hello", "hey", "sup", "what's up", "good morning", "good evening"],
}

def classify_intent(message: str) -> str:
    lower = message.lower().strip()
    for intent, keywords in _INTENT_MAP.items():
        if any(k in lower for k in keywords):
            return intent
    return "chat"


# ── AI call wrapper ────────────────────────────────────────────────────────────
async def _ai(messages: list[dict], temperature: float = 0.7, max_tokens: int = 400) -> str:
    try:
        resp = await _groq.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        err = str(e)
        if "429" in err or "rate_limit" in err.lower():
            return "I'm getting a lot of requests right now. Give me a sec and try again!"
        if "401" in err:
            return "AI configuration error. Please contact support."
        return "I'm having a moment — try again in a few seconds."


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
# In-memory workout session state (survives process restart if using Redis in prod)
_workout_sessions: dict[int, dict] = {}


async def handle_workout_command(
    user_id: int, message: str, intent: str, profile: Profile,
    zone: str, mode: str, db: AsyncSession
) -> ChatResponse:
    from app.services.plan_service import get_exercises_for_slot

    if intent == "show_plan" or (intent == "greeting" and user_id not in _workout_sessions):
        return await _build_greeting(user_id, profile, zone, db)

    if intent == "start_workout":
        return await _start_workout(user_id, profile, zone, mode, db)

    if intent == "next_set" and user_id in _workout_sessions:
        return _next_set(user_id, profile.gender or "male")

    if intent == "done_workout":
        return await _log_and_finish(user_id, profile, db)

    if intent in ("easy", "hard") and user_id in _workout_sessions:
        session = _workout_sessions[user_id]
        mg = session.get("muscle_group", "")
        mem = AIMemory(user_id=user_id, muscle_group=mg, feedback=intent, summary=f"{mg} felt {intent}")
        db.add(mem)
        await db.commit()
        msg = "🔥 Beast mode! I'll push harder next time." if intent == "easy" else "💪 Smart choice. Rest is growth."
        return ChatResponse(reply=f"{msg}\n\nTap **Log Workout** to save.", type="feedback_received")

    return await handle_free_chat(user_id, message, profile, zone, db)


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
    tod = "morning" if h < 12 else ("afternoon" if h < 17 else "evening")
    zone_labels = {"green": "Fully recovered ✅", "yellow": "Moderate recovery ⚠️", "red": "Light day 🔴"}

    if is_rest:
        reply = f"Good {tod}, {profile.name}! 🌟\n\nToday is your **Rest Day** — recovery is where the gains happen.\n\nRecovery: {zone_labels.get(zone, zone)}"
    else:
        reply = f"Good {tod}, {profile.name}! 💪\n\nToday: **{muscle}**\nRecovery: {zone_labels.get(zone, zone)}\n\nSay **'start'** when you're ready!"

    return ChatResponse(
        reply=reply,
        type="daily_plan",
        data={"today": today_slot, "plan": plan_data, "zone": zone, "muscle": muscle}
    )


async def _start_workout(user_id: int, profile: Profile, zone: str, mode: str, db: AsyncSession) -> ChatResponse:
    from app.services.plan_service import get_exercises_for_slot, get_todays_slot

    plan_result = await db.execute(select(WeeklyPlan).where(WeeklyPlan.user_id == user_id))
    plan_row = plan_result.scalar_one_or_none()
    plan_data = plan_row.plan if plan_row else generate_weekly_plan(profile)

    today_slot = get_todays_slot(plan_data) or {"label": "Full Body", "db_key": "full_body"}
    exercises = get_exercises_for_slot(today_slot, profile, zone)
    muscle_group = today_slot.get("label", "Full Body")

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
    intensity = {"green": "Full intensity", "yellow": "Moderate intensity", "red": "Light session"}[zone]
    intro = await _set_intro(ex["name"], 1, profile.gender or "male")

    return ChatResponse(
        reply=f"Let's GO! 🔥 **{muscle_group}** — {intensity}\n\n{intro}\n\n**{ex['name']}**\n{ex.get('weight_guide', '')} · {ex['reps']} reps · {ex['sets']} sets",
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
    import asyncio

    session = _workout_sessions[user_id]
    ex = session["exercises"][session["current_index"]]
    session["current_set"] += 1

    if session["current_set"] > ex["sets"]:
        session["completed"].append(ex["name"])
        session["current_index"] += 1
        session["current_set"] = 1

        if session["current_index"] >= len(session["exercises"]):
            return ChatResponse(
                reply="🎉 **All exercises done!**\n\nHow did that feel?",
                type="workout_all_done",
                data={}
            )

        next_ex = session["exercises"][session["current_index"]]
        return ChatResponse(
            reply=f"➡️ **Next: {next_ex['name']}**\n{next_ex.get('weight_guide', '')} · {next_ex['reps']} reps",
            type="workout_next_exercise",
            data={
                "current_exercise": next_ex,
                "current_exercise_index": session["current_index"],
                "current_set": 1,
                "total_exercises": len(session["exercises"]),
            }
        )

    return ChatResponse(
        reply=f"Set {session['current_set']}/{ex['sets']} 💪\n\n**{ex['name']}** — {ex.get('weight_guide', '')}\n{ex['reps']} reps",
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

    badge_msg = f"\n\n🏅 **New Badge: {new_badge.badge_icon} {new_badge.badge_name}!**" if new_badge else ""
    return ChatResponse(
        reply=f"✅ **Workout logged!** {duration} mins · Streak: {streak} days 🔥{badge_msg}\n\nRest up, hydrate, recover!",
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
    return await _ai([
        {"role": "system", "content": f"You are a fitness coach. Be {tone}. One short sentence only."},
        {"role": "user", "content": f"Set {set_num} of {exercise_name}. Motivate me."},
    ], temperature=0.9, max_tokens=40)


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

    system_prompt = f"""You are FitCoach AI — a personal fitness coach.
User: {profile.name}, {profile.age or ''}yo {profile.gender or ''}, goal: {profile.goal}, level: {profile.level}.
Mode: {profile.active_mode}. Recovery zone: {zone}.
{f'Recent history: {memory_context}' if memory_context else ''}
Be direct, motivating, practical. Max 3 short paragraphs. No generic advice."""

    reply = await _ai([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": msg},
    ], temperature=0.7, max_tokens=300)

    return ChatResponse(reply=reply, type="chat")


def _rule_based_chat(message: str, profile: Profile, zone: str) -> str:
    """Smart rule-based responses when no GROQ API key is configured."""
    lower = message.lower()
    name  = profile.name or "there"
    goal  = profile.goal or "general_fitness"
    level = profile.level or "beginner"

    zone_msg = {
        "green":  "Your recovery is great — you can train hard today! 💪",
        "yellow": "Moderate recovery — keep intensity controlled today.",
        "red":    "Low recovery — today should be a light session or rest day.",
    }.get(zone, "")

    if any(w in lower for w in ["hello", "hi", "hey", "start"]):
        return f"Hey {name}! 💪 Ready to crush it?\n\n{zone_msg}\n\nAsk me about your workout, nutrition, or how to hit your {goal.replace('_', ' ')} goal faster!"

    if any(w in lower for w in ["motivation", "motivat", "inspire"]):
        msgs = {
            "fat_loss":    "Every workout burns fat. Every skipped meal choice matters. You're reshaping your body one decision at a time. 🔥",
            "muscle_gain": "Muscles grow when you're consistent, not when you're perfect. Show up, lift heavy, eat right, sleep well. 💪",
            "strength":    "Strength is built through progressive overload and patience. Trust the process — you're getting stronger every session. ⚡",
        }
        return msgs.get(goal, f"You chose this path for a reason, {name}. Every rep, every meal, every rest day is building the version of you that you want to be. Keep going. 🌟")

    if any(w in lower for w in ["protein", "eat", "food", "diet", "nutrition", "meal"]):
        w = profile.weight or 75
        target = round(w * (2.2 if goal == "muscle_gain" else 1.8))
        return f"For {goal.replace('_', ' ')}, aim for **{target}g protein/day** ({round(target/3)}g per meal).\n\nBest sources: chicken breast, eggs, Greek yogurt, tuna, cottage cheese.\n\nDrink at least {round(w * 0.033, 1)}L water daily. 💧"

    if any(w in lower for w in ["rest", "recover", "sleep", "sore"]):
        return f"Recovery IS training, {name}. 🌙\n\n• Sleep 7–9 hours — this is when muscle grows\n• Eat enough protein to rebuild\n• Light walks on rest days keep blood flowing\n• {zone_msg}"

    if any(w in lower for w in ["cardio", "run", "fat", "burn"]):
        return "For fat loss, **HIIT beats steady-state** for time efficiency.\n\n• 3×/week: 20 min HIIT after weights\n• Fasted walks (30 min morning) for extra fat burning\n• Never sacrifice sleep for cardio — sleep burns fat too!\n\nProtein stays high even on cardio days. 🔥"

    if any(w in lower for w in ["form", "technique", "how to"]):
        return f"Great question about technique, {name}! 📚\n\nKey principles:\n• Control the negative (lowering) phase — 2–3 seconds down\n• Full range of motion beats heavy partial reps\n• If form breaks, drop the weight\n• Record yourself — what you feel and what you do are different!\n\nFor specific exercises, add a GROQ API key in your backend .env for AI coaching."

    if any(w in lower for w in ["plan", "schedule", "week", "today"]):
        return f"Your {level} plan is built for **{goal.replace('_', ' ')}** with {profile.days_per_week or 4} days/week.\n\n{zone_msg}\n\nGo to the Workout tab to see today's session and start tracking. Your plan adapts to your recovery scores! 📅"

    return f"Great question, {name}! 🤖\n\nFor full AI coaching with personalised answers, add your **GROQ API key** to the backend `.env` file (get it free at console.groq.com).\n\n{zone_msg}\n\nMeanwhile, use the Workout tab to start your session!"


# ── Nutrition analysis ─────────────────────────────────────────────────────────
async def analyze_food_ai(food_description: str, image_base64: str | None = None) -> dict:
    """Analyze food and return fields that match the Flutter nutrition UI exactly."""

    # If no API key configured, return a useful estimation instead of an error
    if not settings.GROQ_API_KEY:
        return _estimate_food(food_description)

    prompt = f"""You are a nutrition expert. Analyze this food and return ONLY a valid JSON object with EXACTLY these keys (numbers only, no units):
{{
  "calories": 350,
  "protein_g": 25,
  "carbs_g": 40,
  "fats_g": 10,
  "fibre_g": 5,
  "fitness_rating": "Good for muscle gain",
  "advice": "One sentence of specific coaching advice for this meal.",
  "best_timing": "Best eaten pre/post workout or at specific meal time."
}}

Food to analyze: {food_description}

Return ONLY the JSON object. No markdown, no explanation, just the JSON."""

    messages = [{"role": "user", "content": prompt}]
    if image_base64:
        messages = [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
        ]}]

    raw = await _ai(messages, temperature=0.1, max_tokens=250)

    try:
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            # Ensure all required keys exist with numeric types
            return {
                "calories":      int(data.get("calories", 0)),
                "protein_g":     float(data.get("protein_g", 0)),
                "carbs_g":       float(data.get("carbs_g", 0)),
                "fats_g":        float(data.get("fats_g", 0)),
                "fibre_g":       float(data.get("fibre_g", 0)),
                "fitness_rating": str(data.get("fitness_rating", "Good")),
                "advice":        str(data.get("advice", "")),
                "best_timing":   str(data.get("best_timing", "")),
            }
    except (json.JSONDecodeError, AttributeError, ValueError):
        pass

    return _estimate_food(food_description)


def _estimate_food(food_description: str) -> dict:
    """Rule-based fallback when AI is unavailable. Better than returning zeros."""
    desc = food_description.lower()
    # Very rough heuristic estimates
    calories = 400
    protein_g = 20.0
    carbs_g   = 45.0
    fats_g    = 12.0
    fibre_g   = 4.0

    if any(w in desc for w in ["chicken", "turkey", "fish", "tuna", "egg"]):
        protein_g = 35.0; calories = 320; carbs_g = 5.0; fats_g = 10.0
        rating = "Excellent — high protein, lean"
    elif any(w in desc for w in ["rice", "pasta", "bread", "oat"]):
        carbs_g = 60.0; calories = 380; protein_g = 10.0
        rating = "Good — quality carbs for energy"
    elif any(w in desc for w in ["salad", "vegetable", "broccoli", "spinach"]):
        calories = 150; protein_g = 8.0; carbs_g = 15.0; fats_g = 5.0; fibre_g = 8.0
        rating = "Excellent — nutrient-dense, low calorie"
    elif any(w in desc for w in ["burger", "pizza", "fries", "chips"]):
        calories = 650; fats_g = 30.0; carbs_g = 70.0; protein_g = 20.0
        rating = "Poor — high calorie, eat in moderation"
    elif any(w in desc for w in ["shake", "protein", "whey"]):
        protein_g = 40.0; calories = 250; carbs_g = 20.0; fats_g = 4.0
        rating = "Excellent — post-workout recovery"
    else:
        rating = "Good — balanced meal"

    return {
        "calories":      calories,
        "protein_g":     protein_g,
        "carbs_g":       carbs_g,
        "fats_g":        fats_g,
        "fibre_g":       fibre_g,
        "fitness_rating": rating,
        "advice":        "Add a GROQ API key in your .env for precise AI-powered analysis.",
        "best_timing":   "Works well as a main meal or post-workout refuel.",
    }
