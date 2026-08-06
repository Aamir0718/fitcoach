# 🏋️ FitCoach AI

An AI-powered fitness coaching platform that provides personalized workout plans, real-time posture analysis, recovery tracking, nutrition analysis, and progress monitoring — all inside a modern premium web interface.

---

# ✨ Features

## 🏠 Ultra Premium Home
- Premium animated landing page
- Glassmorphism UI
- Smooth scroll animations
- Interactive hero section
- Dynamic workout highlights
- Premium gradients and effects
- Responsive design

---

## 🤖 AI Coach
- Personalized workout plans
- AI conversational fitness coach
- Gym mode
- Sport mode
- Adaptive workout generation
- Exercise guidance

---

## 👻 Ghost Trainer
- Exercise category selection
- Exercise list by muscle group
- Live camera posture analysis
- AI form feedback
- Rep counter
- Workout timer
- Workout completion tracking

---

## 😴 Recovery Intelligence
- Daily recovery questionnaire
- Recovery score
- Sleep tracking
- Fatigue analysis
- Readiness recommendations
- AI recovery suggestions

---

## 📈 Progress Tracking
- Workout history
- Weekly progress
- Streak tracking
- Personal records
- Workout statistics
- Performance dashboard

---

## 🥗 AI Nutrition
- Food image analysis
- AI food recognition
- Calories estimation
- Protein
- Carbohydrates
- Fat breakdown
- Daily nutrition summary

---

## 👤 Profile
- Athlete profile
- Body metrics
- Goal management
- Workout preferences
- Sport mode setup
- Theme customization

---

# 🛠 Tech Stack

### Frontend
- HTML5
- CSS3
- Vanilla JavaScript
- Chart.js
- Lucide Icons
- Google Fonts

### Backend
- FastAPI
- Python
- Pydantic
- SQLAlchemy
- Alembic

### Database
- PostgreSQL
- Supabase

### AI
- Groq API
- Gemini Vision
- MediaPipe Pose
- AI Nutrition Analysis

---

# 📁 Project Structure

```
FitCoach/
│
├── backend/
│   ├── app/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   └── main.py
│
├── frontend/
│   ├── assets/
│   │   └── images/
│   ├── static/
│   │   ├── css
│   │   ├── js
│   │   ├── home-premium.css
│   │   ├── home-premium-v2.css
│   │   ├── home-premium.js
│   │   ├── home-premium-v2.js
│   │   └── style.css
│   └── index.html
│
└── README.md
```

---

# 🚀 Running the Project

## 1. Clone

```bash
git clone https://github.com/Aamir0718/fitcoach.git
cd fitcoach
```

---

## 2. Create Virtual Environment

```bash
python -m venv .venv
```

Windows

```bash
.venv\Scripts\activate
```

Linux / Mac

```bash
source .venv/bin/activate
```

---

## 3. Install Backend Dependencies

```bash
cd backend

pip install -r requirements.txt
```

---

## 4. Configure Environment

Create a `.env` file inside **backend**

Example

```
DATABASE_URL=...
GROQ_API_KEY=...
GEMINI_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
SECRET_KEY=...
```

---

## 5. Start Backend

```bash
uvicorn app.main:app --reload
```

Backend runs on

```
http://127.0.0.1:8000
```

---

## 6. Open Frontend

Open

```
frontend/index.html
```

or

Serve it with VS Code Live Server.

---

# 📸 Modules

✅ Premium Landing Page

✅ AI Coach

✅ Ghost Trainer

✅ Recovery Dashboard

✅ Progress Dashboard

✅ Nutrition Analysis

✅ Athlete Profile

---

# 🎨 UI Highlights

- Premium Glassmorphism
- Smooth Animations
- Responsive Layout
- Interactive Dashboard
- Gradient Effects
- Dynamic Hero Section
- Modern Sidebar
- Theme Engine
- AI-inspired Design Language

---

# 📷 Assets

Images are stored inside:

```
frontend/assets/images/
```

Includes

- Home hero images
- Athlete images
- Workout images
- Background assets
- Premium landing graphics

---

# 🔮 Upcoming Improvements

- Voice Coach
- Workout History Export
- AI Workout Generator v2
- Advanced Nutrition Detection
- Apple Health Integration
- Google Fit Integration
- Wearable Device Sync
- Dark/Light Auto Themes
- Performance Analytics
- Mobile App

---

# 👨‍💻 Contributors

- Abhinav Kumar
- Aamir

---

# 📄 License

This project is developed for educational and research purposes.

---

# ⭐ Version

Current Version

```
v1.0.0
```

Latest Stable Commit

```
9fa496a
Ultra premium home UI, ghost trainer improvements, workout fixes
```