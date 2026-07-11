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
  }) as unknown as RequestHandler;
}
