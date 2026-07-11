"""Structured JSON logging via structlog.

Rules:
- No print() anywhere in application code.
- All log entries are JSON objects.
- Request IDs are propagated automatically via structlog context variables.
- Log level is configurable from settings.

Usage:
    from app.core.logging import get_logger
    log = get_logger()
    log.info("event_name", key="value")
"""
import logging
import sys

import structlog


def configure_logging(level: str = "info") -> None:
    """Configure structlog for structured JSON output. Call once at startup."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.ExceptionRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "ai-service") -> structlog.BoundLogger:
    """Return a named structlog logger. Request context is merged automatically."""
    return structlog.get_logger(name)
