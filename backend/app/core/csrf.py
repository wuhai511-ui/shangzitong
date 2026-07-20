"""CSRF protection for H5 cookie-authenticated unsafe requests."""
from secrets import compare_digest

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.config import settings


class CSRFMiddleware(BaseHTTPMiddleware):
    """Require a double-submit token when a request uses the H5 session cookie."""

    UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
    SESSION_BOOTSTRAP_PATH = "/api/v1/auth/session"
    CSRF_COOKIE_NAME = "szt_csrf"
    CSRF_HEADER_NAME = "X-CSRF-Token"

    async def dispatch(self, request: Request, call_next):
        if request.method not in self.UNSAFE_METHODS:
            return await call_next(request)

        if (
            request.method == "POST"
            and request.url.path == self.SESSION_BOOTSTRAP_PATH
        ):
            return await call_next(request)

        session_token = request.cookies.get(settings.H5_COOKIE_NAME)
        if not session_token:
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        scheme, separator, bearer_token = authorization.partition(" ")
        if (
            separator
            and scheme.lower() == "bearer"
            and bearer_token.strip()
        ):
            return await call_next(request)

        csrf_cookie = request.cookies.get(self.CSRF_COOKIE_NAME)
        csrf_header = request.headers.get(self.CSRF_HEADER_NAME)
        if not csrf_cookie or not csrf_header or not compare_digest(
            csrf_cookie.encode("utf-8"), csrf_header.encode("utf-8")
        ):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed"},
            )
        return await call_next(request)
