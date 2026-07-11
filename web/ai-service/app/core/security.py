"""Trust boundary with the Node gateway.

The AI service NEVER authenticates end users. It verifies only that a request
originated from the trusted Node gateway (via a shared internal token), then
trusts the user identity the gateway forwards in request headers.

Trust contract:
  Node validates the JWT, resolves the user, enforces RBAC, then calls the
  AI service with:
    X-Internal-Token:    shared secret (required — rejects all other traffic)
    X-User-Id:           validated user ID (required)
    X-User-Role:         e.g. "IT_ADMIN" (required)
    X-User-Department:   e.g. "Engineering" (optional)
    X-Tenant:            e.g. "acme-corp" (optional, defaults to "default")
    X-Request-Id:        correlation ID (optional, generated if absent)

The AI service must NEVER call jwt.decode(), NEVER query a users table.
"""
import hmac

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.constants import (
    HEADER_REQUEST_ID,
    HEADER_TENANT,
    HEADER_USER_DEPARTMENT,
    HEADER_USER_ID,
    HEADER_USER_ROLE,
)


class RequestContext(BaseModel):
    """Validated request context assembled from Node gateway headers.

    All fields are set by the Node gateway before forwarding the request.
    The AI service trusts them unconditionally once the internal token check
    passes — it performs no independent user lookup or permission evaluation.
    """

    user_id: str
    role: str
    department: str | None = None
    tenant: str = "default"
    request_id: str = ""


async def verify_internal_token(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """Dependency: reject any request that does not carry the correct internal token.

    Reads the header name from settings so it can be rotated via env without a
    code change. Uses hmac.compare_digest to prevent timing attacks.
    """
    token = request.headers.get(settings.token_header_name)
    expected = settings.internal_service_token
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal service token.",
        )


async def authenticated_request(
    request: Request,
    _: None = Depends(verify_internal_token),
) -> RequestContext:
    """Dependency: build a validated RequestContext from gateway-forwarded headers.

    Only reachable after verify_internal_token passes. Returns a RequestContext
    ready to be used by route handlers — no further authentication is needed.
    """
    user_id = request.headers.get(HEADER_USER_ID)
    role = request.headers.get(HEADER_USER_ROLE)

    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing forwarded user context headers (X-User-Id, X-User-Role).",
        )

    return RequestContext(
        user_id=user_id,
        role=role,
        department=request.headers.get(HEADER_USER_DEPARTMENT),
        tenant=request.headers.get(HEADER_TENANT, "default"),
        request_id=request.headers.get(HEADER_REQUEST_ID, ""),
    )
