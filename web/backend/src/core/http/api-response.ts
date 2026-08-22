/** Helpers that write the shared API envelope onto an Express response. */
import type { Response } from 'express';
import type { ApiFailure, ApiSuccess } from '@hr-onboarding/shared';

export function sendSuccess<T>(res: Response, data: T, status = 200): void {
  const body: ApiSuccess<T> = {
    success: true,
    data,
    requestId: res.locals.requestId,
  };
  res.status(status).json(body);
}

export function sendFailure(
  res: Response,
  status: number,
  code: string,
  message: string,
  details?: Record<string, string[]>,
): void {
  const body: ApiFailure = {
    success: false,
    error: { code, message, details, requestId: res.locals.requestId },
    requestId: res.locals.requestId,
  };
  res.status(status).json(body);
}

/** Namespace-style helper used in controllers — delegates to the functions above. */
export const ApiResponse = {
  success<T>(res: Response, data: T): void {
    sendSuccess(res, data, 200);
  },
  created<T>(res: Response, data: T): void {
    sendSuccess(res, data, 201);
  },
  failure(res: Response, status: number, code: string, message: string, details?: Record<string, string[]>): void {
    sendFailure(res, status, code, message, details);
  },
};

