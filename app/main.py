import os
import sentry_sdk
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import create_tables
from app.routers import auth, profile, workouts, recovery, progress, nutrition, ai_coach

# ── Sentry (production error tracking) ────────────────────────────────────────
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
    )


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if settings.is_development:
        await create_tables()   # Auto-create in dev; use Alembic in production
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print(f"🚀 FitCoach API running — {settings.ENVIRONMENT}")
    yield
    # Shutdown
    print("👋 FitCoach API shutting down")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="FitCoach AI API",
    version="2.0.0",
    description="AI-powered fitness coaching platform",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)


# ── Middleware ─────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ── Global exception handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.is_development:
        raise exc
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": "An unexpected error occurred. Please try again."},
    )


# ── Static files (progress photos) ────────────────────────────────────────────
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(workouts.router)
app.include_router(recovery.router)
app.include_router(progress.router)
app.include_router(nutrition.router)
app.include_router(ai_coach.router)


# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "env": settings.ENVIRONMENT}


@app.get("/")
async def root():
    return {"message": "FitCoach AI API", "docs": "/docs"}
