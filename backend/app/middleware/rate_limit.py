"""
Simple in-memory rate limiter middleware.
For production, replace with Redis-backed rate limiting.
"""
import time
from collections import defaultdict
from fastapi import Request
from starlette.responses import JSONResponse

rate_limit_store: dict[str, list[float]] = defaultdict(list)

WINDOW_SECONDS = 60  # 1-minute sliding window
ANONYMOUS_LIMIT = 60   # 60 requests per minute for unauthenticated users
AUTHENTICATED_LIMIT = 200  # 200 requests per minute for authenticated users


async def rate_limit_middleware(request: Request, call_next):
    """Rate limit incoming requests based on user identity."""
    # Try to get user_id from request state (set by auth dependency)
    user_id = getattr(request.state, "user_id", None) or "anonymous"

    limit = AUTHENTICATED_LIMIT if user_id != "anonymous" else ANONYMOUS_LIMIT

    now = time.time()
    # Remove entries outside the sliding window
    rate_limit_store[user_id] = [
        t for t in rate_limit_store[user_id] if now - t < WINDOW_SECONDS
    ]

    if len(rate_limit_store[user_id]) >= limit:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please wait a moment."},
        )

    rate_limit_store[user_id].append(now)
    response = await call_next(request)
    return response
