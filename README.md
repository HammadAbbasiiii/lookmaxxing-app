# LookMaxx Web

The **web version** of LookMaxx AI — the same AI facial-analysis engine, delivered as a fast, browser-based web app (no app store, no download, instant link).

This is a **fresh, separate project** from the iOS app (`lookmaxxing-app`).

## Structure

- `backend/` — the reusable **FastAPI AI engine** (auth, photo upload, ML facial analysis, 90-day plan, product recommendations, progress). Copied cleanly from the original project; includes the 94 MB PyTorch ranking model. Deployable via `backend/render.yaml`.
- `frontend/` — the web frontend (to be built).

## Status

- **Backend:** complete and test-covered. Runs locally and deploys to Render.
- **Frontend:** in planning.

## Getting started (backend)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in real values
uvicorn app.main:app --reload
```

Interactive API docs: http://localhost:8000/docs
