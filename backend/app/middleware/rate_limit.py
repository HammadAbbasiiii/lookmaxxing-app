"""
Rate limiter middleware — Redis-backed with an in-memory fallback.

Uses a fixed sliding window per identity (user_id or "anonymous"). Redis makes
the limit shared across every worker/instance — the previous in-memory dict only
ever limited a single process, which is a real hole on any multi-worker deploy.
If Redis is unreachable, it degrades to the in-memory store so the API keeps
working (and still rate-limits per process).
"""
import time
from collections import defaultdict
from fastapi import Request
from starlette.responses import JSONResponse

WINDOW_SECONDS = 60  # 1-minute sliding window
ANONYMOUS_LIMIT = 60   # 60 requests per minute for unauthenticated users
AUTHENTICATED_LIMIT = 200  # 200 requests per minute for authenticated users

# In-process fallback store
_fallback_store: dict[str, list[float]] = defaultdict(list)

_redis = None
_redis_checked = False


def _extract_user_id(request: Request):
    """Pull the authenticated user id from the bearer token, if present.

    The rate limiter is a pure middleware (it runs *before* the auth dependency),
    so it can't rely on ``get_current_user``. We do a lightweight JWT decode of
    the Authorization header here; on any failure we simply fall back to the
    anonymous bucket. This gives authenticated users their own, larger bucket
    instead of sharing the anonymous one — previously ``request.state.user_id``
    was never populated anywhere, so *every* request was rate-limited as
    "anonymous" (a single shared bucket + dead authenticated code path).
    """
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    try:
        from jose import jwt as _jwt
        from app.config import settings as _settings

        payload = _jwt.decode(
            token, _settings.SECRET_KEY, algorithms=[_settings.ALGORITHM]
        )
        sub = payload.get("sub")
        return f"user:{sub}" if sub else None
    except Exception:
        return None


def _get_redis():
    """Lazily connect to Redis once; return None if unavailable."""
    global _redis, _redis_checked
    if _redis_checked:
        return _redis
    _redis_checked = True
    try:
        import redis as _r
        from app.config import settings
        _redis = _r.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )
        _redis.ping()
    except Exception:
        _redis = None
    return _redis


async def rate_limit_middleware(request: Request, call_next):
    """Rate limit incoming requests based on user identity."""
    user_id = (
        getattr(request.state, "user_id", None)
        or _extract_user_id(request)
        or "anonymous"
    )
    limit = AUTHENTICATED_LIMIT if user_id != "anonymous" else ANONYMOUS_LIMIT

    r = _get_redis()
    if r is not None:
        try:
            key = f"rl:{user_id}"
            now = time.time()
            window_start = now - WINDOW_SECONDS
            member = f"{now}:{id(request)}"
            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {member: now})
            pipe.zcard(key)
            pipe.expire(key, WINDOW_SECONDS)
            _removed, _added, count, _exp = pipe.execute()
            if count is not None and int(count) > limit:
                # Don't let the rejected request inflate the window.
                r.zrem(key, member)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please wait a moment."},
                )
            return await call_next(request)
        except Exception:
            pass  # Redis failed mid-request — fall through to in-memory store

    # In-memory fallback
    now = time.time()
    _fallback_store[user_id] = [
        t for t in _fallback_store[user_id] if now - t < WINDOW_SECONDS
    ]
    if len(_fallback_store[user_id]) >= limit:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please wait a moment."},
        )
    _fallback_store[user_id].append(now)
    return await call_next(request)
