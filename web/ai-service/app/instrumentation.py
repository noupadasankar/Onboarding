"""
OpenTelemetry instrumentation for the AI service (FastAPI).
Initializes tracing, metrics, and logging exports.
"""
import os
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from prometheus_client import start_http_server


def init_telemetry() -> tuple[TracerProvider, MeterProvider]:
    """Initialize OpenTelemetry tracing, metrics, and logging."""
    service_name = os.getenv("OTEL_SERVICE_NAME", "optiagent-ai-service")
    environment = os.getenv("NODE_ENV", os.getenv("ENVIRONMENT", "development"))
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://localhost:4318/v1/traces")
    prometheus_port = int(os.getenv("PROMETHEUS_PORT", "9465"))

    # Create resource with service metadata
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: service_name,
        ResourceAttributes.SERVICE_VERSION: "0.1.0",
        ResourceAttributes.DEPLOYMENT_ENVIRONMENT: environment,
    })

    # Configure trace provider with OTLP exporter
    trace_provider = TracerProvider(resource=resource)
    trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(trace_provider)

    # Configure metrics with Prometheus exporter
    prometheus_reader = PrometheusMetricReader()
    metric_provider = MeterProvider(resource=resource, metric_readers=[prometheus_reader])
    metrics.set_meter_provider(metric_provider)

    # Start Prometheus metrics HTTP server
    start_http_server(prometheus_port)

    # Auto-instrument FastAPI, HTTPX, and logging
    FastAPIInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=True)

    print(f"OpenTelemetry initialized for {service_name} (env: {environment})")
    print(f"Prometheus metrics available at http://localhost:{prometheus_port}/metrics")

    return trace_provider, metric_provider