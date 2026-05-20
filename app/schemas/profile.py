from pydantic import BaseModel, field_validator
from typing import Optional


class OnboardingStep(BaseModel):
    """Single onboarding field update."""
    field: str
    value: str | int | float | bool


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    goal: Optional[str] = None
    level: Optional[str] = None
    workout_place: Optional[str] = None
    days_per_week: Optional[int] = None
    injuries: Optional[str] = None
    plays_sport: Optional[bool] = None
    sport: Optional[str] = None
    sport_role: Optional[str] = None
    sport_focus: Optional[str] = None
    sport_position: Optional[str] = None
    match_frequency: Optional[str] = None
    sport_injuries: Optional[str] = None
    bowling_type: Optional[str] = None
    onboarding_complete: Optional[bool] = None   # allow card-flow to force True

    @field_validator("gender")
    @classmethod
    def valid_gender(cls, v):
        if v and v not in ("male", "female"):
            raise ValueError("gender must be male or female")
        return v

    @field_validator("workout_place")
    @classmethod
    def valid_place(cls, v):
        if v and v not in ("gym", "home"):
            raise ValueError("workout_place must be gym or home")
        return v


def xp_level_info(xp: int) -> dict:
    thresholds = [(0, "Rookie"), (500, "Athlete"), (2000, "Beast"), (5000, "Legend")]
    level_name = "Rookie"
    next_threshold = 500
    for threshold, name in thresholds:
        if xp >= threshold:
            level_name = name
    # find next threshold
    for threshold, _ in thresholds:
        if threshold > xp:
            next_threshold = threshold
            break
    else:
        next_threshold = None
    return {
        "level_name": level_name,
        "xp": xp,
        "xp_to_next": (next_threshold - xp) if next_threshold else None,
        "next_threshold": next_threshold,
    }


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    name: Optional[str]
    age: Optional[int]
    gender: Optional[str]
    height: Optional[float]
    weight: Optional[float]
    goal: Optional[str]
    level: Optional[str]
    workout_place: Optional[str]
    days_per_week: Optional[int]
    injuries: Optional[str]
    plays_sport: bool
    sport: Optional[str]
    sport_role: Optional[str]
    sport_focus: Optional[str]
    match_frequency: Optional[str]
    onboarding_complete: bool
    sport_onboarding_complete: bool
    bmi: Optional[float]
    active_mode: str
    xp: int = 0
    level_name: Optional[str] = None
    xp_to_next: Optional[int] = None

    class Config:
        from_attributes = True


class SportOnboardRequest(BaseModel):
    sport: str
    role: Optional[str] = None
    position: Optional[str] = None
    focus: Optional[str] = None
    match_frequency: Optional[str] = None
    bowling_type: Optional[str] = None
    injuries: Optional[str] = None
