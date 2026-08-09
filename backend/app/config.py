from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def _guard_production_secrets(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.JWT_SECRET == "change-this-in-production":
                raise ValueError("JWT_SECRET must be set to a real secret in production.")
            if len(self.JWT_SECRET) < 32:
                raise ValueError("JWT_SECRET must be at least 32 characters in production.")
            # Wildcard CORS + allow_credentials=True (main.py) lets any site make
            # authenticated requests on a logged-in user's behalf — set
            # ALLOWED_ORIGINS to the real frontend origin(s) in prod env vars.
            if "*" in self.ALLOWED_ORIGINS:
                raise ValueError("ALLOWED_ORIGINS must not contain '*' in production. Set explicit origins.")
        return self

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://fitcoach:password@localhost:5432/fitcoach_db"
    DATABASE_URL_SYNC: str = "postgresql://fitcoach:password@localhost:5432/fitcoach_db"

    # USDA API
    USDA_API_KEY: str = ""

    # Security
    JWT_SECRET: str = "change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Email — Brevo (preferred, verified single sender, no domain needed) → Resend → SMTP fallback
    BREVO_API_KEY: str = ""           # xkeysib- key from brevo.com, verified sender required
    RESEND_API_KEY: str = ""          # get free at resend.com (100/day free)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    EMAIL_FROM: str = "FitCoach AI <noreply@fitcoach.ai>"

    # AI
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_VISION_MODEL: str = "llama-3.2-11b-vision-preview"  # Vision-capable model for image analysis
    USDA_API_KEY: str = ""  # USDA FoodData Central API key for nutrition data
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # App
    ENVIRONMENT: str = "development"
    # Dev defaults only — production MUST set ALLOWED_ORIGINS to the real
    # frontend origin(s) via env var. No "*": it's rejected in production
    # (see _guard_production_secrets) because allow_credentials=True in
    # main.py's CORS middleware makes a wildcard origin a same-site-request-
    # forgery hole — any site could call the API using a logged-in user's cookies/token.
    ALLOWED_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:5500",  # VS Code Live Server
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    ]
    SENTRY_DSN: str = ""

    # Storage
    STORAGE_BACKEND: str = "local"
    UPLOAD_DIR: str = "./uploads"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
