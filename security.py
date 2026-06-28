"""Authentication and authorization dependencies for the NexusAI API.

Provides FastAPI dependencies that validate an API key / bearer token sourced
through ``get_settings()``. Two tiers exist:

- ``require_identity``  -> any valid user or admin key (used by ``/chat``).
- ``require_admin``     -> the admin key only (used by ``/settings``, ``/upload``,
  ``/documents``).

Keys may be supplied either via the ``X-API-Key`` header or an
``Authorization: Bearer <key>`` header. Comparison is constant-time.

Graceful degradation: if no keys are configured in settings, the API refuses
access (fail-closed) rather than silently allowing everyone — exposing the app
without configured keys is exactly the C3 gap we are closing.
"""

import hmac
import logging

from fastapi import Depends, Header, HTTPException, status

from llm.factory import get_settings

LOGGER = logging.getLogger(__name__)


def _extract_key(x_api_key: str | None, authorization: str | None) -> str | None:
    if x_api_key:
        return x_api_key.strip()
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
    return None


def _matches(candidate: str | None, *valid_keys: str) -> bool:
    if not candidate:
        return False
    for key in valid_keys:
        if key and hmac.compare_digest(candidate, key):
            return True
    return False


async def require_identity(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> str:
    """Authenticate any valid caller (user or admin). Returns the identity tier."""
    settings = get_settings()
    candidate = _extract_key(x_api_key, authorization)

    if not (settings.api_key or settings.admin_api_key):
        LOGGER.error("No API_KEY/ADMIN_API_KEY configured; rejecting request (fail-closed).")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured.",
        )

    if _matches(candidate, settings.admin_api_key):
        return "admin"
    if _matches(candidate, settings.api_key):
        return "user"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_admin(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> str:
    """Authenticate an admin caller. Returns the identity tier ("admin")."""
    settings = get_settings()
    candidate = _extract_key(x_api_key, authorization)

    if not settings.admin_api_key:
        LOGGER.error("No ADMIN_API_KEY configured; rejecting admin request (fail-closed).")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin authentication is not configured.",
        )

    if _matches(candidate, settings.admin_api_key):
        return "admin"

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin credentials required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
