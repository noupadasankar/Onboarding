"""Health, liveness, and readiness endpoints.

Three probes serve different purposes in production:
  /health  — general status (returned to upstreams, load balancers)
  /live    — "is the process running?" (never fails while the process is alive)
  /ready   — "can the service accept traffic?" (later: checks ChromaDB, embedding model)

All three are unauthenticated so that orchestration platforms can probe them
without a service token. A guarded /whoami endpoint demonstrates the gateway
trust contract.
"""
from fastapi import APIRouter, Depends

from app.core.constants import SERVICE_NAME
from app.core.security import RequestContext, authenticated_request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """General service health — always 200 while the process is running."""
    return {"status": "ok", "service": SERVICE_NAME}


@router.get("/live")
async def liveness() -> dict[str, str]:
    """Liveness probe — confirms the process is alive."""
    return {"status": "alive", "service": SERVICE_NAME}


@router.get("/ready")
async def readiness() -> dict[str, str]:
    """Readiness probe — confirms the service can accept traffic.

    Later increments will add dependency checks here (ChromaDB connectivity,
    embedding model availability). Returns 200 for now.
    """
    return {"status": "ready", "service": SERVICE_NAME}


@router.get("/whoami")
async def whoami(ctx: RequestContext = Depends(authenticated_request)) -> RequestContext:
    """Guarded endpoint — reachable only via the Node gateway.

    Returns the full RequestContext assembled from forwarded headers.
    Demonstrates the trust contract: internal token required, JWT never touched.
    Remove or restrict in production if not needed.
    """
    return ctx
