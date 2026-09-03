# LookMaxx AI — Web

AI facial analysis + personalized 90-day lookmaxxing plan, delivered as a web app.

## Structure

- `backend/` — FastAPI AI engine (auth, photo upload, ML facial analysis, 90-day plan, product recommendations, progress)
- `web/` — web frontend (in progress)

## Quick start (backend)

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs
