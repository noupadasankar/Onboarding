/**
 * Distributed rate limiter (Redis fixed-window counter). Shared across all
 * backend instances so limits hold under horizontal scaling. Built as a factory
 * keyed by a caller-supplied bucket name (e.g. "login") + client IP.
 */
import type { RequestHandler } from 'express';
import type { RedisService } from '../infrastructure/cache/redis.service';
import { RateLimitError } from '../core/errors/app-error';
import { asyncHandler } from '../core/http/async-handler';

interface RateLimitOptions {
  bucket: string;
  max: number;
  windowSeconds: number;
}

export function createRateLimiter(
  redis: RedisService,
  options: RateLimitOptions,
): RequestHandler {
  const { bucket, max, windowSeconds } = options;

  return asyncHandler(async (req, res, next) => {
    const ip = req.ip ?? 'unknown';
    const key = `ratelimit:${bucket}:${ip}`;

    const count = await redis.client.incr(key);
    if (count === 1) {
      await redis.client.expire(key, windowSeconds);
    }
    if (count > max) {
      const ttl = await redis.client.ttl(key);
      res.setHeader('Retry-After', Math.max(ttl, 0));
      throw new RateLimitError('Too many attempts, please try again later');
    }
    res.setHeader('X-RateLimit-Limit', max);
    res.setHeader('X-RateLimit-Remaining', Math.max(max - count, 0));
    next();
  });
}
