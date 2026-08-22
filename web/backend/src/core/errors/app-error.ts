/**
 * Domain/application error. Carries an HTTP status + machine-readable code so the
 * error-handler middleware can translate it into the shared API envelope without
 * leaking stack traces to clients.
 */
import { ErrorCode } from '@hr-onboarding/shared';

export class AppError extends Error {
  readonly statusCode: number;
  readonly code: ErrorCode | string;
  readonly details?: Record<string, string[]>;
  /** Expected (operational) errors are safe to surface; unexpected ones are masked. */
  readonly isOperational: boolean;

  constructor(
    message: string,
    statusCode: number,
    code: ErrorCode | string,
    options?: { details?: Record<string, string[]>; isOperational?: boolean },
  ) {
    super(message);
    this.name = new.target.name;
    this.statusCode = statusCode;
    this.code = code;
    this.details = options?.details;
    this.isOperational = options?.isOperational ?? true;
    Error.captureStackTrace?.(this, new.target);
  }
}

// --- Convenience factories for the common cases ---

export class BadRequestError extends AppError {
  constructor(message = 'Bad request', details?: Record<string, string[]>) {
    super(message, 400, ErrorCode.VALIDATION, { details });
  }
}

export class UnauthorizedError extends AppError {
  constructor(message = 'Unauthenticated', code: ErrorCode = ErrorCode.UNAUTHENTICATED) {
    super(message, 401, code);
  }
}

export class ForbiddenError extends AppError {
  constructor(message = 'Forbidden') {
    super(message, 403, ErrorCode.FORBIDDEN);
  }
}

export class NotFoundError extends AppError {
  constructor(message = 'Not found') {
    super(message, 404, ErrorCode.NOT_FOUND);
  }
}

export class ConflictError extends AppError {
  constructor(message = 'Conflict') {
    super(message, 409, ErrorCode.CONFLICT);
  }
}

export class RateLimitError extends AppError {
  constructor(message = 'Too many requests') {
    super(message, 429, ErrorCode.RATE_LIMITED);
  }
}
