"""FastAPI application factory.

main.py wires together the application — it does not contain logic.
Business logic lives in feature routers; cross-cutting setup lives in core/.

Responsibilities:
  - Create the FastAPI instance
  - Attach lifespan (startup/shutdown)
  - Register middleware
  - Register exception handlers
  - Mount routers
"""
import time
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.constants import API_V1_PREFIX, HEADER_REQUEST_ID, HEADER_USER_ID
from app.core.exceptions import register_exception_handlers
from app.core.lifespan import lifespan
from app.core.logging import get_logger


class _RequestMiddleware(BaseHTTPMiddleware):
    """Assigns a correlation ID, binds structlog context, and logs every request.

    Runs on every request including health probes. User ID is extracted from the
    forwarded gateway header when present; public endpoints log "-" instead.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = request.headers.get(HEADER_REQUEST_ID, str(uuid4()))
        user_id = request.headers.get(HEADER_USER_ID, "-")

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, user_id=user_id)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        log = get_logger()
        log.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )

        response.headers[HEADER_REQUEST_ID] = request_id
        return response


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="OptiAgent AI Service",
        version="0.1.0",
        description=(
            "AI workloads for OptiAgent: document ingestion, RAG pipeline, "
            "LangGraph agents. Receives authenticated requests from the Node gateway only."
        ),
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    # ── Middleware (order matters: added last = runs first) ───────────────────
    app.add_middleware(_RequestMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ────────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=API_V1_PREFIX)

    return app


app = create_app()
