"""Password-reset token generation, hashing and per-email throttling.

Security properties:
- Tokens are 256-bit, generated with ``secrets`` (cryptographically secure), and
  only ever stored as a SHA-256 digest — the raw token exists solely in the email.
- A per-email throttle (default 5 per 15 min) stops reset-link bombing of a
  single victim address; the global rate-limiter also caps per-IP traffic.
"""
import hashlib
import secrets
import time

# Per-email anti-bombing throttle (in-memory; global limiter covers per-IP).
THROTTLE_WINDOW_SECONDS = 900  # 15 minutes
THROTTLE_MAX_REQUESTS = 5      # requests per window per email

_throttle: dict[str, list[float]] = {}


def generate_reset_token() -> str:
    """Return a URL-safe random token with ~256 bits of entropy."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 hex digest of the raw token — what we persist, never the token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_throttled(email: str) -> bool:
    key = email.strip().lower()
    now = time.time()
    times = [t for t in _throttle.get(key, []) if now - t < THROTTLE_WINDOW_SECONDS]
    _throttle[key] = times
    return len(times) >= THROTTLE_MAX_REQUESTS


def record_request(email: str) -> None:
    key = email.strip().lower()
    _throttle.setdefault(key, []).append(time.time())


def reset_throttle() -> None:
    """Clear the in-memory throttle (test fixture)."""
    _throttle.clear()
