from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import date


class ExerciseSchema(BaseModel):
    name: str
    sets: int
    reps: str
    rest: str
    muscle: str
    weight_guide: str
    equipment_required: bool = False
    demo_url: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    mode: Optional[str] = None  # gym | home | sport


class ChatResponse(BaseModel):
    reply: str
    type: str
    data: Optional[dict] = None


class WorkoutLogRequest(BaseModel):
    muscle_group: str
    exercises_done: Optional[str] = None
    duration: int
    mode: str
    sport: Optional[str] = None
    zone: Optional[str] = None
    notes: Optional[str] = None
    date: Optional[date] = None


class WorkoutResponse(BaseModel):
    id: int
    date: date
    muscle_group: Optional[str]
    duration: Optional[int]
    completed: bool
    mode: Optional[str]
    sport: Optional[str]
    zone: Optional[str]
    notes: Optional[str]
    exercises_done: Optional[str]

    class Config:
        from_attributes = True


class WeeklyPlanResponse(BaseModel):
    plan: dict
    mode: Optional[str]
    updated_at: Optional[Any]

    class Config:
        from_attributes = True


class SwapRequest(BaseModel):
    from_day: int
    to_day: int


class WorkoutFinishRequest(BaseModel):
    muscle_group: Optional[str] = "Mixed"
    duration_minutes: int = 0
    exercises_done: List[str] = []
    zone: Optional[str] = "green"
    notes: Optional[str] = None
    exercises: Optional[List[Any]] = []


class PRRequest(BaseModel):
    exercise_name: str
    weight: float
    reps: int
    date: Optional[date] = None
    notes: Optional[str] = None


# ── Set Logging (progressive overload) ────────────────────────────────────────

class SetLogRequest(BaseModel):
    exercise_name: str
    set_number: int = 1
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    feedback: Optional[str] = None  # easy | perfect | hard
    workout_id: Optional[int] = None
    date: Optional[date] = None


class SetLogResponse(BaseModel):
    id: int
    exercise_name: str
    set_number: int
    reps: Optional[int]
    weight_kg: Optional[float]
    feedback: Optional[str]
    is_pr: bool
    date: date

    class Config:
        from_attributes = True


class ProgressiveOverloadResponse(BaseModel):
    exercise_name: str
    last_weight_kg: Optional[float]
    suggested_weight_kg: Optional[float]
    last_reps: Optional[int]
    last_session_date: Optional[str]
    pr_weight_kg: Optional[float]
    message: str


# ── FCM Token ─────────────────────────────────────────────────────────────────

class FCMTokenRequest(BaseModel):
    token: str
    platform: Optional[str] = "android"  # android | ios | web


# ── Exercise Swap ──────────────────────────────────────────────────────────────

class ExerciseSwapRequest(BaseModel):
    slot_key: str
    exercise_name: str  # name of exercise to replace
    zone: Optional[str] = "green"
