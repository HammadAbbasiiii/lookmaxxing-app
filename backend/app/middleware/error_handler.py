"""
Global error handler middleware.
Catches unhandled exceptions to prevent 502 errors when the service is under load.
"""
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def global_error_handler(request: Request, call_next):
    """Wrap every request in a try/except to prevent crashes from bubbling up."""
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger.exception(f"⚠️ Unhandled error on {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error — the service team has been notified.",
                "path": request.url.path,
            },
        )