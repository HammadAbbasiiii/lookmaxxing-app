from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.routes import health, auth, photos, analysis, plan, products, upload
from app.routes import profile, progress, dashboard
from app.middleware.rate_limit import rate_limit_middleware
from app.middleware.error_handler import global_error_handler
from app.database import engine
from app.models import Base
# ── Startup (minimal to stay under 512 MB Render limit) ────────────
print("🚀 LookMaxx API starting …")

# Database tables (only thing loaded at boot to stay under 512 MB)
try:
    Base.metadata.create_all(bind=engine)
    print("✅ DB tables ready")
except Exception as e:
    print(f"⚠️ DB failed: {e}")

# PyTorch model, MediaPipe & Redis are all lazy-loaded on first request.
# Loading the 94MB model at boot consumes 200-300MB and OOMs Render starter tier.

# ── Verify MediaPipe model file exists and attempt lightweight import check ──
import os
_model_paths = [
    os.path.join(os.path.dirname(__file__), "ml", "face_landmarker.task"),
    "/opt/render/project/src/backend/app/ml/face_landmarker.task",
]
_model_found = any(os.path.exists(p) for p in _model_paths)
if _model_found:
    print(f"✅ MediaPipe model file found at startup")
else:
    print("⚠️ MediaPipe model file MISSING at startup — predictions will use mock landmarks")

# Attempt to load MediaPipe early so we can see errors in Render logs
if _model_found:
    try:
        import mediapipe as _mp
        print(f"🔍 MediaPipe version: {_mp.__version__}")
        from mediapipe.tasks import python as _mp_tasks
        from mediapipe.tasks.python import vision as _mp_vision
        print(f"✅ MediaPipe Task API imports successful")
    except Exception as _mp_e:
        print(f"⚠️ MediaPipe import failed at startup: {_mp_e}")

app = FastAPI(
    title="LookMaxx API",
    description="AI-powered looks analysis and improvement platform",
    version="0.1.0"
)

# CORS - allow iOS app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your app's domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression — compress responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=500)

# Global error handler — outermost middleware, catches all unhandled exceptions
app.middleware("http")(global_error_handler)

# Rate limiting — prevent API abuse
app.middleware("http")(rate_limit_middleware)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(photos.router, prefix="/api/v1", tags=["Photos"])
app.include_router(upload.router, prefix="/api/v1", tags=["Upload"])
app.include_router(analysis.router, prefix="/api/v1", tags=["Analysis"])
app.include_router(plan.router, prefix="/api/v1", tags=["Plan"])
app.include_router(products.router, prefix="/api/v1", tags=["Products"])
app.include_router(profile.router, prefix="/api/v1", tags=["Profile"])
app.include_router(progress.router, prefix="/api/v1", tags=["Progress"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard"])
