"""Application lifespan: startup and shutdown hooks.

Kept separate from main.py so that startup tasks can grow without cluttering
the application factory. Later increments will add connection warm-up here
(ChromaDB client, embedding model, LangGraph graph compilation).
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger()

    log.info(
        "ai_service_startup",
        env=settings.app_env,
        port=settings.app_port,
        log_level=settings.log_level,
    )

    yield

    log.info("ai_service_shutdown")
