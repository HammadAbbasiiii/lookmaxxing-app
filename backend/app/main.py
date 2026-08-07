from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.routes import health, auth, photos, analysis, plan, products
from app.routes import profile, progress, dashboard
from app.middleware.rate_limit import rate_limit_middleware
from app.database import engine
from app.models import Base
from app.services.prediction_service import prediction_service

# ── Startup initialisation ─────────────────────────────────────────
print("🚀 LookMaxx API starting up …")

# 1. Database tables
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created/verified")
except Exception as e:
    print(f"⚠️ Database connection failed: {e}")

# 2. ML prediction model
try:
    prediction_service.load_model()
    print("✅ ML prediction model loaded")
except Exception as e:
    print(f"⚠️ Model loading failed (will use mock predictions): {e}")

# 3. Redis (lazy init — just test the connection once)
try:
    from app.config import settings
    redis_url = settings.REDIS_URL
    if redis_url and redis_url != "redis://localhost:6379":
        import redis as redis_lib
        r = redis_lib.Redis.from_url(redis_url, socket_connect_timeout=5)
        r.ping()
        r.close()
        print("✅ Redis connected — caching enabled")
    else:
        print("⚠️ REDIS_URL not set — caching disabled")
except Exception as e:
    print(f"⚠️ Redis connection failed: {e}")

# 4. MediaPipe face landmarker (download + load)
try:
    from app.services.face_analysis_service import download_mediapipe_model, load_face_landmarker
    download_mediapipe_model()
    landmarker = load_face_landmarker()
    if landmarker:
        print("✅ MediaPipe model loaded — real facial landmarks active")
    else:
        print("⚠️ MediaPipe model not available — will use fallback landmarks")
except Exception as e:
    print(f"⚠️ MediaPipe initialisation failed: {e}")

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
