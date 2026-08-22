/**
 * HTTP access logging via pino-http, correlated with the request id. Built as a
 * factory so the configured Pino logger is injected (no module-level singletons).
 */
import { pinoHttp } from 'pino-http';
import type { RequestHandler } from 'express';
import type { Logger } from '../core/logging/logger';

export function createRequestLogger(logger: Logger): RequestHandler {
  return pinoHttp({
    logger,
    genReqId: (_req, res) => (res as unknown as { locals: { requestId?: string } }).locals.requestId ?? '',
    customLogLevel: (_req, res, err) => {
      if (err || res.statusCode >= 500) return 'error';
      if (res.statusCode >= 400) return 'warn';
      return 'info';
    },
    customProps: (_req, res) => ({
      requestId: (res as unknown as { locals: { requestId?: string } }).locals.requestId,
      // Add trace context for distributed tracing correlation
      traceId: (res as unknown as { locals: { traceId?: string } }).locals.traceId,
      spanId: (res as unknown as { locals: { spanId?: string } }).locals.spanId,
    }),
    customSuccessMessage: (req, res) => {
      const requestId = (res as unknown as { locals: { requestId?: string } }).locals.requestId;
      return `${req.method} ${req.url} ${res.statusCode} [${requestId}]`;
    },
    customErrorMessage: (req, res, err) => {
      const requestId = (res as unknown as { locals: { requestId?: string } }).locals.requestId;
      return `${req.method} ${req.url} ${res.statusCode} ERROR [${requestId}]: ${err.message}`;
    },
    quietReqLogger: true, // Prevent duplicate logging
  }) as unknown as RequestHandler;
}
