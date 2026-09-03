from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.routes import health, auth, photos, analysis, plan, products, upload
from app.routes import profile, progress, dashboard, explore, analytics, admin_products
from app.routes import entitlements, coach, payments
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

# ── Lightweight migration ────────────────────────────────────────────
# create_all() creates NEW tables (e.g. analytics_events) but never alters
# existing ones, so add users.is_admin if the column is missing.
try:
    from sqlalchemy import inspect as _inspect, text as _text
    _insp = _inspect(engine)
    _cols = {c["name"] for c in _insp.get_columns("users")}
    if "is_admin" not in _cols:
        with engine.begin() as _conn:
            _conn.execute(_text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE"))
        print("✅ Migrated: added users.is_admin")
except Exception as _mig_e:
    print(f"⚠️ users.is_admin migration skipped: {_mig_e}")

# ── Migrate: add later profile columns (skin_type, skin_concerns, commitment) ──
try:
    from sqlalchemy import inspect as _inspect2, text as _text2
    _insp2 = _inspect2(engine)
    _cols2 = {c["name"] for c in _insp2.get_columns("users")}
    _additions = {
        "skin_type": "VARCHAR(20)",
        "skin_concerns": "JSON",
        "commitment": "VARCHAR(20)",
    }
    for _col, _type in _additions.items():
        if _col not in _cols2:
            with engine.begin() as _conn2:
                _conn2.execute(_text2(f"ALTER TABLE users ADD COLUMN {_col} {_type}"))
            print(f"✅ Migrated: added users.{_col}")
except Exception as _mig_e2:
    print(f"⚠️ users profile columns migration skipped: {_mig_e2}")

# ── Recovery: reset photos orphaned at "processing" by a prior OOM crash ──
try:
    from app.database import SessionLocal
    from app.models import Photo
    _db = SessionLocal()
    try:
        _stuck = _db.query(Photo).filter(Photo.analysis_status == "processing").all()
        for _p in _stuck:
            _p.analysis_status = "failed"
            _p.analysis_details = {
                "error": "Analysis interrupted by service restart — please re-upload.",
            }
        if _stuck:
            _db.commit()
            print(f"🔁 Recovered {len(_stuck)} photo(s) stuck at 'processing'")
    finally:
        _db.close()
except Exception as _recovery_e:
    print(f"⚠️ Recovery scan failed: {_recovery_e}")

# ── Seed product catalogue from JSON (one-time, idempotent) ─────────
try:
    from app.database import SessionLocal as _SL
    from app.models import Product as _Product
    from app.services.product_recommendation_service import _load_product_database
    _seed_db = _SL()
    try:
        if _seed_db.query(_Product).count() == 0:
            _seed_products = _load_product_database()
            for _sp in _seed_products:
                _seed_db.add(
                    _Product(
                        id=_sp.get("id"),
                        name=_sp.get("name", ""),
                        brand=_sp.get("brand"),
                        category=_sp.get("category", "general"),
                        price=float(_sp.get("price") or 0),
                        currency=_sp.get("currency", "USD"),
                        tier=_sp.get("tier", "mid_range"),
                        image_url=_sp.get("image_url"),
                        affiliate_url=_sp.get("affiliate_link"),
                        description=_sp.get("social_proof"),
                        rating=_sp.get("rating"),
                        review_count=int(_sp.get("reviews_count") or 0),
                        tags=_sp.get("tags"),
                        recommended_for=_sp.get("recommended_for"),
                        social_proof=_sp.get("social_proof"),
                        is_active=True,
                    )
                )
            _seed_db.commit()
            print(f"🌱 Seeded {len(_seed_products)} products from JSON")
    finally:
        _seed_db.close()
except Exception as _seed_e:
    print(f"⚠️ Product seed skipped: {_seed_e}")

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
app.include_router(explore.router, prefix="/api/v1", tags=["Explore"])
app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])
app.include_router(admin_products.router, prefix="/api/v1", tags=["Admin"])
app.include_router(entitlements.router, prefix="/api/v1", tags=["Entitlements"])
app.include_router(coach.router, prefix="/api/v1", tags=["Coach"])
app.include_router(payments.router, prefix="/api/v1", tags=["Payments"])
