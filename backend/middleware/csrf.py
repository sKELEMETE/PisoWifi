import logging
from urllib.parse import urlparse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

import config

logger = logging.getLogger(__name__)


class CSRFTokenMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection for cookie-authenticated admin endpoints.

    Protection layers (defense-in-depth):
      1. Origin header validation  — rejects cross-origin requests
      2. X-CSRF-Token header check — rejects requests without matching token

    Only state-changing requests to /api/admin/ paths are checked.
    """

    EXEMPT_PATHS = {"/api/admin/login", "/api/admin/logout"}

    def _origin_allowed(self, origin: str | None) -> bool:
        if not origin:
            return True
        try:
            parsed = urlparse(origin)
            origin_host = f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
            for allowed in config.CORS_ORIGINS:
                allowed_parsed = urlparse(allowed) if "://" in allowed else urlparse(f"http://{allowed}")
                allowed_host = f"{allowed_parsed.hostname}:{allowed_parsed.port}" if allowed_parsed.port else allowed_parsed.hostname
                if origin_host == allowed_host:
                    return True
        except Exception:
            pass
        return False

    async def dispatch(self, request, call_next):
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            path = request.url.path
            if path.startswith("/api/admin/") and path not in self.EXEMPT_PATHS:
                origin = request.headers.get("Origin")
                if not self._origin_allowed(origin):
                    logger.warning("CSRF origin validation failed for %s %s (Origin: %s)", request.method, path, origin)
                    return JSONResponse(
                        status_code=403,
                        content={
                            "success": False,
                            "message": "CSRF validation failed",
                            "errors": ["Invalid or missing CSRF token"],
                        },
                    )

                cookie_token = request.cookies.get("csrf_token")
                header_token = request.headers.get("X-CSRF-Token")
                if not cookie_token or not header_token or cookie_token != header_token:
                    logger.warning("CSRF token validation failed for %s %s", request.method, path)
                    return JSONResponse(
                        status_code=403,
                        content={
                            "success": False,
                            "message": "CSRF validation failed",
                            "errors": ["Invalid or missing CSRF token"],
                        },
                    )
        response = await call_next(request)
        return response
