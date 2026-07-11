/**
 * Assigns/propagates a correlation id per request. Reuses an inbound
 * `x-request-id` when present (e.g. from NGINX) or generates one; echoes it back
 * on the response and stores it in `res.locals` for logging + the API envelope.
 */
import type { RequestHandler } from 'express';
import { randomUUID } from 'node:crypto';
import { HEADER_REQUEST_ID } from '../config/constants';

export const requestId: RequestHandler = (req, res, next) => {
  const incoming = req.header(HEADER_REQUEST_ID);
  const id = incoming && incoming.length <= 128 ? incoming : randomUUID();
  res.locals.requestId = id;
  res.setHeader(HEADER_REQUEST_ID, id);
  next();
};
