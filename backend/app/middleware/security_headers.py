"""Security response headers middleware (§19).

Adds a small, safe set of hardening headers to every response. These are pure
defense-in-depth for a JSON API — no CSP is set here because the backend never
serves HTML, and a CSP on JSON would be meaningless while adding noise.
"""

from starlette.responses import Response

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}


async def security_headers_middleware(request, call_next) -> Response:
    response = await call_next(request)
    for name, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response
