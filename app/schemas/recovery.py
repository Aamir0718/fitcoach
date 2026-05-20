from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date


class RecoveryLogRequest(BaseModel):
    sleep_hours: float
    sleep_quality: int    # 1-5
    fatigue: int          # 1-5
    soreness: int         # 1-5
    prev_load: int        # 1-5

    @field_validator("sleep_hours")
    @classmethod
    def valid_sleep(cls, v):
        if not (2 <= v <= 12):
            raise ValueError("sleep_hours must be between 2 and 12")
        return v

    @field_validator("sleep_quality", "fatigue", "soreness", "prev_load")
    @classmethod
    def valid_scale(cls, v):
        if not (1 <= v <= 5):
            raise ValueError("Scale values must be between 1 and 5")
        return v


class RecoveryResponse(BaseModel):
    id: int
    date: date
    sleep_hours: Optional[float]
    sleep_quality: Optional[int]
    fatigue: Optional[int]
    soreness: Optional[int]
    prev_load: Optional[int]
    score: Optional[int]
    zone: Optional[str]

    class Config:
        from_attributes = True
