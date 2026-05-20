from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional


class SignupRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SendOTPRequest(BaseModel):
    email: EmailStr
    purpose: str  # verify | login | reset

    @field_validator("purpose")
    @classmethod
    def valid_purpose(cls, v: str) -> str:
        if v not in ("verify", "login", "reset"):
            raise ValueError("purpose must be verify, login, or reset")
        return v


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str
    purpose: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    reset_token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    onboarding_complete: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class OTPLoginRequest(BaseModel):
    email: EmailStr
    otp: str
