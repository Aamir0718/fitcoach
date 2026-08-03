# ⚡ FitCoach AI

An AI-powered fitness coaching platform that provides personalized workouts, nutrition analysis, recovery tracking, and intelligent food recognition using Computer Vision and AI.

---

# 🚀 Features

### 🏋️ AI Fitness Coach
- AI-powered fitness assistant using Groq LLM
- Personalized workout recommendations
- Chat-driven onboarding
- Goal-based workout generation
- Beginner, Intermediate and Advanced plans

### 🥗 Smart Nutrition Analysis
- Upload meal images
- YOLOv8 food detection
- USDA FoodData Central nutrition lookup
- Automatic macro calculation
- Calories
- Protein
- Carbohydrates
- Fat
- Fiber
- Sugar
- Health score
- Nutrition tips

### 🤖 AI Food Verification
To improve accuracy, the application verifies uncertain food detections.

Workflow:

```
Image
    ↓
YOLOv8 Detection
    ↓
Confidence Check
    ↓
High Confidence
    ↓
USDA Nutrition

OR

Low Confidence
    ↓
AI Food Verification Popup
    ↓
User Confirmation
    ↓
USDA Nutrition
```

This prevents visually similar foods (Paneer, Cheese, Pizza, etc.) from producing incorrect nutrition reports.

### 📈 Progress Tracking
- Workout streaks
- Weight tracking
- XP system
- Badges
- Progress analytics

### 💪 Recovery Tracking
- Recovery score
- Sleep tracking
- Fatigue analysis
- Soreness tracking
- Readiness insights

### 🔐 Authentication
- JWT Authentication
- OTP Email Verification
- Password Reset
- Secure Login

---

# 📂 Project Structure

```text
fitcoach/
│
├── frontend/
│   ├── index.html
│   └── static/
│       ├── style.css
│       ├── script.js
│       ├── assets/
│       └── js/
│
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── database.py
│   │   ├── config.py
│   │   ├── main.py
│   │   ├── models/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── ai_service.py
│   │   │   ├── nutrition_service.py
│   │   │   ├── food_detector.py
│   │   │   └── ...
│   │   └── utils/
│   │
│   ├── models/
│   │   └── best.pt
│   │
│   ├── uploads/
│   ├── alembic/
│   └── requirements.txt
│
└── README.md
```

---

# 🛠 Tech Stack

### Frontend
- HTML5
- CSS3
- JavaScript
- Chart.js

### Backend
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic

### AI
- Groq API
- YOLOv8 (Ultralytics)
- USDA FoodData Central API

### Authentication
- JWT
- OTP Email Verification
- Brevo / Resend / SMTP

---

# 📋 Prerequisites

- Python 3.11+
- PostgreSQL
- Groq API Key
- USDA FoodData Central API Key
- Brevo API Key (recommended)

---

# ⚙ Backend Setup

```bash
cd backend

python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

Copy

```text
.env.example
```

to

```text
.env
```

---

# 🔑 Required Environment Variables

| Variable | Description |
|-----------|-------------|
| DATABASE_URL | PostgreSQL Async URL |
| DATABASE_URL_SYNC | PostgreSQL Sync URL |
| JWT_SECRET | JWT Secret |
| GROQ_API_KEY | AI Coach |
| USDA_API_KEY | USDA Nutrition API |
| BREVO_API_KEY | OTP Email |
| ALLOWED_ORIGINS | Frontend URLs |

---

# 🧠 YOLO Food Detection

The application uses a custom trained YOLOv8 model.

Current supported classes include:

- Apple
- Banana
- Burger
- Chapathi
- Chicken Gravy
- Fries
- Idli
- Pizza
- Rice
- Soda
- Tomato
- Vada

Model location:

```text
backend/models/best.pt
```

---

# 🥗 USDA Nutrition Integration

Detected food names are mapped to USDA FoodData Central.

Returned nutrients include:

- Calories
- Protein
- Carbohydrates
- Fat
- Fiber
- Sugar

Nutrition values are calculated automatically and displayed in the dashboard.

---

# ▶ Run Backend

```bash
python -m alembic upgrade head

python -m uvicorn app.main:app --reload
```

API

```
http://localhost:8000
```

Swagger Docs

```
http://localhost:8000/docs
```

---

# ▶ Run Frontend

```bash
cd frontend

python -m http.server 5000
```

Open

```
http://localhost:5000
```

---

# 📡 Important API Endpoints

| Method | Endpoint | Description |
|----------|---------------------------|-------------------------|
| POST | /api/auth/signup | Create account |
| POST | /api/auth/login | Login |
| POST | /api/auth/send-otp | Send OTP |
| POST | /api/auth/verify-otp | Verify OTP |
| GET | /api/profile/me | User profile |
| PUT | /api/profile/me | Update profile |
| POST | /api/coach/chat | AI Coach |
| POST | /api/nutrition/analyze | AI Nutrition Analysis |
| GET | /api/progress | Progress Dashboard |
| GET | /api/recovery/latest | Latest Recovery |
| GET | /health | Health Check |

---

# 🚀 Deployment

### Frontend
- Vercel
- Netlify
- GitHub Pages

### Backend
- Render
- Railway
- VPS
- Docker

---

# ✨ Highlights

- AI Fitness Coach
- YOLOv8 Food Detection
- USDA Nutrition Analysis
- AI Food Verification
- Recovery Tracking
- Progress Analytics
- JWT Authentication
- OTP Email Verification
- Responsive UI
- FastAPI Backend
- PostgreSQL Database
- Computer Vision + AI Integration

---

# 📸 Workflow

```
User Uploads Meal
        │
        ▼
YOLOv8 Food Detection
        │
        ▼
Confidence Evaluation
        │
 ┌──────┴────────┐
 │               │
 ▼               ▼
High         Low Confidence
Confidence         │
 │                 ▼
 ▼         AI Food Verification
 │                 │
 ▼                 ▼
USDA Nutrition Lookup
        │
        ▼
Nutrition Analysis
        │
        ▼
Calories • Protein • Carbs • Fat • Fiber • Sugar
        │
        ▼
Health Report
```

---

# 👨‍💻 Contributors

Developed collaboratively as part of the **FitCoach AI** project with ongoing enhancements in AI nutrition analysis, food detection, workout intelligence, and user experience.