/**
 * Extracts and propagates W3C trace-context headers (traceparent, tracestate).
 * Ensures distributed tracing context.
 */
import type { RequestHandler } from 'express';
import { propagation, context, trace, SpanStatusCode, SpanKind } from '@opentelemetry/api';

export const traceContextMiddleware: RequestHandler = (req, res, next) => {
  // Extract trace context from incoming headers
  const extractedContext = propagation.extract(context.active(), req.headers);

  // Start a new span for this request (or continue the extracted one)
  const tracer = trace.getTracer('optiagent-backend');
  const span = tracer.startSpan(`${req.method} ${req.path}`, {
    kind: SpanKind.SERVER,
    attributes: {
      'http.method': req.method,
      'http.url': req.url,
      'http.route': req.route?.path ?? req.path,
      'http.target': req.path,
      'http.scheme': req.protocol,
      'http.host': req.get('host') ?? '',
      'http.user_agent': req.get('user-agent') ?? '',
      'http.client_ip': req.ip ?? req.socket.remoteAddress ?? '',
    },
  }, extractedContext);

  // Store span in response locals for access in route handlers
  res.locals.span = span;
  res.locals.traceId = span.spanContext().traceId;
  res.locals.spanId = span.spanContext().spanId;

  // Propagate trace context in response headers
  // Create a new context with the span set, then inject
  const spanContext = trace.setSpan(context.active(), span);
  const outputHeaders: Record<string, string> = {};
  propagation.inject(spanContext, outputHeaders);
  Object.entries(outputHeaders).forEach(([key, value]) => {
    res.setHeader(key, value);
  });

  // End span when response finishes
  res.on('finish', () => {
    span.setAttribute('http.status_code', res.statusCode);
    if (res.statusCode >= 400) {
      span.setStatus({ code: SpanStatusCode.ERROR, message: `HTTP ${res.statusCode}` });
    }
    span.end();
  });

  res.on('close', () => {
    if (!res.writableEnded) {
      span.end();
    }
  });

  next();
};

/**
 * Get the current active span from response locals (set by traceContextMiddleware).
 */
export function getActiveSpan(res: express.Response): ReturnType<typeof trace.getTracer>['startSpan'] | null {
  return res.locals.span ?? null;
}

/**
 * Add custom attributes to the current request span.
 */
export function addSpanAttributes(res: express.Response, attributes: Record<string, unknown>): void {
  const span = res.locals.span;
  if (span) {
    Object.entries(attributes).forEach(([key, value]) => {
      span.setAttribute(key, value);
    });
  }
}

/**
 * Record an exception on the current request span.
 */
export function recordSpanException(res: express.Response, error: Error): void {
  const span = res.locals.span;
  if (span) {
    span.recordException(error);
    span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
  }
}

// Need to import express types
import express from 'express';