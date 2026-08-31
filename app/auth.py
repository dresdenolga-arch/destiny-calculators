"""Site-wide HTTP Basic Auth, gated by env vars.

If SITE_USER / SITE_PASSWORD are not both set, auth is skipped entirely —
that's the local-dev default. Set both in the hosting provider's dashboard
to lock the deployed site down to people you share the password with.
"""
import base64
import os
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

SITE_USER = os.environ.get("SITE_USER")
SITE_PASSWORD = os.environ.get("SITE_PASSWORD")


class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not SITE_USER or not SITE_PASSWORD:
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                user, _, password = decoded.partition(":")
            except Exception:
                user, password = "", ""
            if secrets.compare_digest(user, SITE_USER) and secrets.compare_digest(password, SITE_PASSWORD):
                return await call_next(request)

        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Restricted"'},
        )
