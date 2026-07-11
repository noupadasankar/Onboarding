/**
 * Wraps an async Express handler so rejected promises are forwarded to the error
 * middleware instead of crashing the process. Controllers stay free of try/catch.
 */
import type { NextFunction, Request, RequestHandler, Response } from 'express';

type AsyncHandler = (req: Request, res: Response, next: NextFunction) => Promise<unknown>;

export function asyncHandler(handler: AsyncHandler): RequestHandler {
  return (req, res, next) => {
    handler(req, res, next).catch(next);
  };
}
