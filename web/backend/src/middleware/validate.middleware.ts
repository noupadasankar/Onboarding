/**
 * Request-validation middleware. Validates and *replaces* the chosen request
 * segment with the parsed (typed, coerced) value, so controllers receive clean
 * data. Uses shared Zod schemas — validation is defined once and reused FE + BE.
 */
import type { RequestHandler } from 'express';
import { ZodError, type ZodTypeAny } from 'zod';

type Segment = 'body' | 'query' | 'params';

export function validate(schema: ZodTypeAny, segment: Segment = 'body'): RequestHandler {
  return (req, _res, next) => {
    try {
      const parsed = schema.parse(req[segment]);
      // Reassign the parsed value (coerced/normalized) back onto the request.
      Object.defineProperty(req, segment, { value: parsed, writable: true, configurable: true });
      next();
    } catch (error) {
      // Forward Zod errors to the central handler, which shapes field details.
      next(error instanceof ZodError ? error : error);
    }
  };
}
