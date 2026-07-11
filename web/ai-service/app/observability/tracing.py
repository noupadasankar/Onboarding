"""Distributed tracing helpers — OpenTelemetry-compatible span context.

In development, tracing is a no-op. In production, configure an OTEL
exporter (Jaeger, Zipkin, Azure Monitor) and set OTEL_EXPORTER_* env vars.

Usage::

    with trace_span("supervisor_node", attributes={"agent": "hr"}) as span:
        result = await supervisor_node(state)
        span.set_attribute("selected_agent", result.get("selected_agent"))
"""
from __future__ import annotations

import contextlib
import time
from typing import Any, Generator

from app.core.logging import get_logger

_log = get_logger()

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    _tracer = trace.get_tracer("optiagent")
    _otel_available = True
except ImportError:  # pragma: no cover
    _otel_available = False
    _tracer = None  # type: ignore[assignment]


class _NoOpSpan:
    """Fallback span when OTEL is not installed."""

    def set_attribute(self, key: str, value: Any) -> None:  # noqa: ARG002
        pass

    def record_exception(self, exc: Exception) -> None:  # noqa: ARG002
        pass

    def set_status(self, *args: Any, **kwargs: Any) -> None:
        pass


@contextlib.contextmanager
def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> Generator[_NoOpSpan | Any, None, None]:
    """Context manager that creates an OTEL span or a no-op fallback.

    Always yields a span-like object with ``set_attribute`` / ``record_exception``.
    """
    if _otel_available and _tracer:
        with _tracer.start_as_current_span(name) as span:
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, v)
            t0 = time.monotonic()
            try:
                yield span
            finally:
                span.set_attribute("duration_ms", round((time.monotonic() - t0) * 1000, 1))
    else:
        span = _NoOpSpan()
        if attributes:
            _log.debug("trace_span_start", name=name, **attributes)
        t0 = time.monotonic()
        try:
            yield span
        finally:
            _log.debug(
                "trace_span_end",
                name=name,
                duration_ms=round((time.monotonic() - t0) * 1000, 1),
            )


def get_trace_id() -> str:
    """Return the current OTEL trace ID as a hex string, or empty string."""
    if not _otel_available:
        return ""
    current_span = trace.get_current_span()
    ctx = current_span.get_span_context()
    if ctx and ctx.is_valid:
        return format(ctx.trace_id, "032x")
    return ""
