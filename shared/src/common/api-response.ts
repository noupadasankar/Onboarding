/**
 * Uniform API envelope. Every backend response — success or failure — uses one of
 * these shapes so the frontend has a single, predictable contract to parse.
 */
import type { ErrorCode } from '../errors/error-codes.js';

export interface ApiError {
  code: ErrorCode | string;
  message: string;
  /** Field-level validation issues, keyed by dotted path. */
  details?: Record<string, string[]>;
  /** Correlates a client error with backend logs. */
  requestId?: string;
}

export interface ApiSuccess<T> {
  success: true;
  data: T;
  requestId?: string;
}

export interface ApiFailure {
  success: false;
  error: ApiError;
  requestId?: string;
}

export type ApiResponse<T> = ApiSuccess<T> | ApiFailure;

/** Cursor-free offset pagination envelope for list endpoints. */
export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export function isApiFailure<T>(res: ApiResponse<T>): res is ApiFailure {
  return res.success === false;
}
