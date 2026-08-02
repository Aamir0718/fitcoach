# ⚡ FitCoach AI

AI-powered fitness coaching platform — chat-driven onboarding, personalized workout plans, recovery tracking, and nutrition analysis.

## Project structure

```
fitcoach/
├── frontend/           ← Static web app (plain HTML/CSS/JS, no build step)
│   ├── index.html
│   └── static/
│       ├── style.css
│       ├── script.js
│       └── js/
│
└── backend/            ← FastAPI API
    ├── app/
    │   ├── main.py
    │   ├── config.py
    │   ├── database.py
    │   ├── models/
    │   ├── routers/
    │   ├── schemas/
    │   ├── services/
    │   └── core/
    ├── alembic/         ← DB migrations
    └── requirements.txt
```

## Prerequisites

- Python 3.11.9 (see `backend/.python-version`)
- A Postgres database — easiest free option: create a project at [supabase.com](https://supabase.com) and use its connection string (the **session pooler** string works on any network, including IPv4-only ones)
- A free [Groq API key](https://console.groq.com) (used for the AI coach chat)
- A free [Brevo API key](https://app.brevo.com) with a verified sender (used to send OTP emails) — or a Resend key, or Gmail SMTP as fallbacks

## Backend setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\python.exe -m pip install -r requirements.txt
# macOS/Linux
venv/bin/python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in real values:

```bash
cp .env.example .env
```

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | Async Postgres URL, e.g. `postgresql+asyncpg://user:pass@host:5432/postgres` |
| `DATABASE_URL_SYNC` | Yes | Same DB, sync driver, used by Alembic — `postgresql://user:pass@host:5432/postgres` |
| `JWT_SECRET` | Yes | Any long random string for local dev; must be 32+ chars in production |
| `GROQ_API_KEY` | Yes | Powers the AI coach chat and plan generation |
| `BREVO_API_KEY` | Recommended | `xkeysib-...` key from Brevo → Settings → SMTP & API → API Keys. Needs a verified sender email. |
| `RESEND_API_KEY` | Optional | Fallback if Brevo isn't set — note: unverified Resend accounts can only send to their own account email |
| `SMTP_USER` / `SMTP_PASS` / `SMTP_HOST` / `SMTP_PORT` | Optional | Last-resort email fallback |
| `ALLOWED_ORIGINS` | Yes | JSON array of allowed frontend origins, e.g. `["http://localhost:5000"]` |

If no email provider is configured, OTP codes are printed to the server console and returned in the API response as `otp_fallback` — the app still works end-to-end for local testing.

Run migrations, then start the server:

```bash
venv/Scripts/python.exe -m alembic upgrade head
venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API docs: `http://localhost:8000/docs`

**Windows note:** if you see a `UnicodeEncodeError` on startup (from an emoji in a log line), run with `-X utf8`:
```bash
venv/Scripts/python.exe -X utf8 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Frontend setup

No build step — any static file server works:

```bash
cd frontend
python -m http.server 5000
```

Open `http://localhost:5000`. `frontend/static/script.js` auto-detects `localhost` and points API calls at `http://localhost:8000`; in production it points at the deployed backend URL (update the `API` constant near the top of the file if your backend URL changes).

## Deployment

- **Frontend** → static hosting (Vercel). `vercel.json` at the repo root serves `frontend/` directly, no build step.
- **Backend** → needs a persistent server, not serverless (it uses background DB connections and is designed for Render — see `backend/render.yaml`). Vercel's serverless functions won't work for this backend as-is.

## API endpoints (selected)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/signup` | No | Create account |
| POST | `/api/auth/login` | No | Get access + refresh tokens |
| POST | `/api/auth/send-otp` | No | Send OTP for verify/login/reset |
| POST | `/api/auth/verify-otp` | No | Verify an OTP code |
| GET/PUT | `/api/profile/me` | Yes | Get/update profile |
| POST | `/api/coach/chat` | Yes | Main AI coach chat — drives onboarding, workouts, and plan generation |
| GET | `/api/progress/` | Yes | Analytics: streaks, badges, weight trend, heatmap |
| POST | `/api/nutrition/analyze` | Yes | AI food/nutrition analysis |
| GET | `/health` | No | Health check |

Full interactive list at `/docs` once the backend is running.
