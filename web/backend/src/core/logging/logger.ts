/**
 * Structured logger (Pino). No `console.log` anywhere in application code — this
 * is the single logging surface, injected via the DI container.
 */
import pino, { type Logger } from 'pino';
import type { AppConfig } from '../../config/env';
import { trace, SpanStatusCode } from '@opentelemetry/api';

export type { Logger };

/**
 * Create a Pino logger with OpenTelemetry trace correlation and standard fields.
 */
export function createLogger(config: AppConfig): Logger {
  const baseLogger = pino({
    level: config.logLevel,
    // Redact anything that could carry secrets/PII out of logs.
    redact: {
      paths: [
        'req.headers.authorization',
        'req.headers.cookie',
        'req.body.password',
        '*.password',
        '*.passwordHash',
        '*.accessToken',
        '*.refreshToken',
        '*.secret',
        '*.apiKey',
        '*.token',
      ],
      remove: true,
    },
    base: {
      service: 'backend',
      environment: config.nodeEnv,
      version: process.env.npm_package_version ?? '0.1.0',
    },
    transport: config.isProduction
      ? undefined
      : { target: 'pino-pretty', options: { colorize: true, translateTime: 'SYS:HH:MM:ss' } },
    // Add OpenTelemetry trace context to all log entries
    mixin: () => {
      const span = trace.getActiveSpan();
      if (!span) return {};

      const spanContext = span.spanContext();
      return {
        traceId: spanContext.traceId,
        spanId: spanContext.spanId,
        traceFlags: spanContext.traceFlags,
      };
    },
  });

  return baseLogger;
}

/**
 * Create a child logger with additional context bound to all log lines.
 * Useful for service-level loggers: `const logger = createChildLogger(base, { module: 'auth' })`
 */
export function createChildLogger(parent: Logger, bindings: Record<string, unknown>): Logger {
  return parent.child(bindings);
}

/**
 * Log an error with standardized fields and optional span recording.
 */
export function logError(
  logger: Logger,
  error: Error | unknown,
  message: string,
  context?: Record<string, unknown>,
): void {
  const err = error instanceof Error ? error : new Error(String(error));
  const span = trace.getActiveSpan();

  if (span) {
    span.recordException(err);
    span.setStatus({ code: SpanStatusCode.ERROR, message: err.message });
  }

  logger.error(
    {
      err: { message: err.message, stack: err.stack, name: err.name },
      ...context,
    },
    message,
  );
}

/**
 * Log an audit event (immutable, structured).
 * These should be forwarded to a separate audit log sink.
 */
export function logAudit(
  logger: Logger,
  event: {
    action: string;
    resource: string;
    resourceId?: string;
    userId?: string;
    tenantId?: string;
    outcome: 'success' | 'failure' | 'denied';
    metadata?: Record<string, unknown>;
  },
): void {
  logger.info(
    {
      audit: true,
      ...event,
      timestamp: new Date().toISOString(),
    },
    `AUDIT: ${event.action} on ${event.resource} ${event.outcome}`,
  );
}
