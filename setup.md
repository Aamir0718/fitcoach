Terminal 1 (Backend)
cd backend
.\venv\Scripts\Activate
python -m uvicorn app.main:app --reload

Terminal 2 (Frontend)
cd frontend
python -m http.server 5000

http://localhost:5000
