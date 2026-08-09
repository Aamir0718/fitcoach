import os
try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None
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
if settings.SENTRY_DSN and sentry_sdk:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
    )


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run Alembic migrations on every startup — safe to run repeatedly
    try:
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True, text=True
        )
        print(f"[Alembic] {result.stdout.strip() or 'No output'}")
        if result.returncode != 0:
            print(f"[Alembic ERROR] {result.stderr.strip()}")
    except Exception as e:
        print(f"[Alembic] Could not run migrations: {e}")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print(f"🚀 FitCoach API running — {settings.ENVIRONMENT}")
    yield
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
    import traceback
    tb = traceback.format_exc()
    print(f"[500 ERROR] {request.method} {request.url}\n{tb}")
    if settings.is_production:
        # Never leak stack traces / exception internals to clients in prod —
        # Sentry (initialized above) already has the full trace.
        return JSONResponse(status_code=500, content={"ok": False, "error": "Internal server error"})
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": str(exc), "detail": tb[-500:]},
    )


# ── Static files (progress photos) ────────────────────────────────────────────
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ── Frontend static files ─────────────────────────────────────────────────────
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_dir, "static")), name="static")


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

# ── Serve frontend index.html for development ───────────────────────────────
from fastapi.responses import FileResponse

@app.get("/app")
async def serve_frontend():
    frontend_index = os.path.join(frontend_dir, "index.html")
    if os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    return {"message": "Frontend not found"}
