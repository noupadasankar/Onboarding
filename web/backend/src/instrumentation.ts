/**
 * OpenTelemetry instrumentation setup for the Node.js backend.
 * Initializes tracing, metrics, and logging exports.
 */
import { NodeSDK } from '@opentelemetry/sdk-node';
import { ExpressInstrumentation } from '@opentelemetry/instrumentation-express';
import { HttpInstrumentation } from '@opentelemetry/instrumentation-http';
import { PinoInstrumentation } from '@opentelemetry/instrumentation-pino';
import { PrometheusExporter } from '@opentelemetry/exporter-prometheus';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';
import { diag, DiagConsoleLogger, DiagLogLevel } from '@opentelemetry/api';

if (process.env.OTEL_DEBUG === 'true') {
  diag.setLogger(new DiagConsoleLogger(), DiagLogLevel.DEBUG);
}

const resource = new Resource({
  [SemanticResourceAttributes.SERVICE_NAME]: 'optiagent-backend',
  [SemanticResourceAttributes.SERVICE_VERSION]: process.env.npm_package_version ?? '0.1.0',
  [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: process.env.NODE_ENV ?? 'development',
});

const traceExporter = new OTLPTraceExporter({
  url: process.env.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT ?? 'http://localhost:4318/v1/traces',
});

const prometheusExporter = new PrometheusExporter(
  { port: Number(process.env.PROMETHEUS_PORT) || 9464 },
  () => console.log(`Prometheus scrape endpoint: http://localhost:${process.env.PROMETHEUS_PORT || 9464}/metrics`),
);

export const otelSdk = new NodeSDK({
  resource,
  traceExporter,
  metricReader: prometheusExporter,
  instrumentations: [
    new HttpInstrumentation(),
    new ExpressInstrumentation(),
    new PinoInstrumentation(),
  ],
});

export function startOtel(): void {
  otelSdk.start();
  console.log('OpenTelemetry initialized');
}

export function stopOtel(): Promise<void> {
  return otelSdk.shutdown();
}

process.on('SIGTERM', async () => {
  await stopOtel();
  process.exit(0);
});

process.on('SIGINT', async () => {
  await stopOtel();
  process.exit(0);
});
