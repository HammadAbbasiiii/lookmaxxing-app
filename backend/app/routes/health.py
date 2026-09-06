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
    """Get current max RSS in MB (Linux/macOS only)."""
    try:
        import resource
        import sys
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # macOS reports ru_maxrss in bytes; Linux reports it in kilobytes.
        divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
        return {"max_rss_mb": round(usage.ru_maxrss / divisor, 1)}
    except Exception:
        return None


@router.get("/health")
async def health_check():
    """Health check — used by Render to verify service liveness.

    Kept deliberately lightweight: the iOS app pings this during analysis to
    keep the free-tier worker warm, so it must never trigger heavy imports
    (MediaPipe / torch model loading) or slow DB work.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "lookmaxx-api",
        "redis": _get_redis_status(),
        "memory": _get_memory_usage(),
    }


@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to LookMaxx API",
        "version": "0.1.0",
        "docs": "/docs",
    }
