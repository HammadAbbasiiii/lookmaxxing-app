from fastapi import APIRouter
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_redis_status() -> str:
    """Check Redis connectivity."""
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        return "not_configured"
    try:
        import redis
        r = redis.Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        r.ping()
        return "connected"
    except Exception:
        return "disconnected"


def _get_memory_usage() -> dict | None:
    """Get current memory usage in MB (Linux/Mac only)."""
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return {
            "max_rss_mb": round(usage.ru_maxrss / (1024 * 1024), 1) if os.name != "posix" else round(usage.ru_maxrss / 1024, 1),
        }
    except Exception:
        return None


@router.get("/health")
async def health_check():
    """Health check — used by Render to verify service liveness."""
    import os
    # Check if MediaPipe model file exists
    model_paths = [
        os.path.join(os.path.dirname(__file__), "..", "ml", "face_landmarker.task"),
        "/opt/render/project/src/backend/app/ml/face_landmarker.task",
    ]
    mediapipe_available = any(os.path.exists(p) for p in model_paths)
    model_path = next((p for p in model_paths if os.path.exists(p)), None)

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "lookmaxx-api",
        "redis": _get_redis_status(),
        "memory": _get_memory_usage(),
        "mediapipe_available": mediapipe_available,
        "mediapipe_model_path": model_path,
    }


@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to LookMaxx API",
        "version": "0.1.0",
        "docs": "/docs",
    }
