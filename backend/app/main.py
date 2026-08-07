from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.routes import health, auth, photos, analysis, plan, products
from app.routes import profile, progress, dashboard
from app.middleware.rate_limit import rate_limit_middleware
from app.database import engine
from app.models import Base
from app.services.prediction_service import prediction_service

# ── Startup (minimal to stay under 512 MB Render limit) ────────────
print("🚀 LookMaxx API starting …")

# Database tables
try:
    Base.metadata.create_all(bind=engine)
    print("✅ DB tables ready")
except Exception as e:
    print(f"⚠️ DB failed: {e}")

# ML prediction model (lightweight PyTorch model)
try:
    prediction_service.load_model()
    print("✅ ML model loaded")
except Exception as e:
    print(f"⚠️ ML model failed (using mocks): {e}")

# MediaPipe & Redis are lazy-loaded on demand to save memory
# (MediaPipe alone uses 200+ MB, would OOM on Render starter tier if loaded at boot)

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

# Rate limiting — prevent API abuse
app.middleware("http")(rate_limit_middleware)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(photos.router, prefix="/api/v1", tags=["Photos"])
app.include_router(analysis.router, prefix="/api/v1", tags=["Analysis"])
app.include_router(plan.router, prefix="/api/v1", tags=["Plan"])
app.include_router(products.router, prefix="/api/v1", tags=["Products"])
app.include_router(profile.router, prefix="/api/v1", tags=["Profile"])
app.include_router(progress.router, prefix="/api/v1", tags=["Progress"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard"])
