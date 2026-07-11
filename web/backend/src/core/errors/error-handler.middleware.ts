/**
 * Terminal error-handling middleware. Converts any thrown error into the shared
 * API failure envelope. Unexpected errors are logged in full but masked to the
 * client (no internals leak). Registered last in the middleware chain.
 */
import type { ErrorRequestHandler } from 'express';
import { ZodError } from 'zod';
import { ErrorCode } from '@optiagent/shared';
import type { Logger } from '../logging/logger';
import { sendFailure } from '../http/api-response';
import { AppError } from './app-error';

/** Not-found handler for unmatched routes (registered just before the error handler). */
export const notFoundHandler: ErrorRequestHandler = (_err, _req, res) => {
  sendFailure(res, 404, ErrorCode.NOT_FOUND, 'Route not found');
};

function zodDetails(error: ZodError): Record<string, string[]> {
  const details: Record<string, string[]> = {};
  for (const issue of error.issues) {
    const key = issue.path.join('.') || '_';
    (details[key] ??= []).push(issue.message);
  }
  return details;
}

export function createErrorHandler(logger: Logger): ErrorRequestHandler {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  return (error, req, res, _next) => {
    const requestId = res.locals.requestId as string | undefined;

    if (error instanceof ZodError) {
      sendFailure(res, 400, ErrorCode.VALIDATION, 'Validation failed', zodDetails(error));
      return;
    }

    if (error instanceof AppError) {
      if (!error.isOperational) {
        logger.error({ err: error, requestId }, 'Non-operational AppError');
      }
      sendFailure(res, error.statusCode, error.code, error.message, error.details);
      return;
    }

    // Unknown / unexpected — log everything. In non-production, also surface the
    // real message + any Prisma error code to the client to speed up debugging.
    logger.error({ err: error, requestId, path: req.path }, 'Unhandled error');

    if (process.env['NODE_ENV'] !== 'production') {
      const e = error as { name?: string; message?: string; code?: string; meta?: unknown };
      sendFailure(res, 500, ErrorCode.INTERNAL, e?.message ?? 'Internal server error', {
        name: [e?.name ?? 'Error'],
        ...(e?.code ? { prismaCode: [String(e.code)] } : {}),
        ...(e?.meta ? { meta: [JSON.stringify(e.meta)] } : {}),
      });
      return;
    }

    sendFailure(res, 500, ErrorCode.INTERNAL, 'Internal server error');
  };
}
