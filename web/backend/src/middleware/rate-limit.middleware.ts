/**
 * Rate limiting middleware using Redis token bucket.
 * Provides both per-IP and per-user rate limiting with configurable windows.
 */
import { inject, injectable } from 'inversify';
import type { RedisService } from '@infrastructure/cache/redis.service';
import { TYPES } from '@core/di/types';
import type { Request, Response, NextFunction } from 'express';
import { AppError } from '@core/errors/app-error';
import { ErrorCode } from '@optiagent/shared';

export interface RateLimitOptions {
  bucket: string;
  max: number;
  windowSeconds: number;
  keyPrefix?: string;
  keyFn?: (req: Request) => string;
}

export interface RateLimitInfo {
  limit: number;
  remaining: number;
  reset: number;
  retryAfter?: number;
}

/**
 * Redis-backed token bucket rate limiter.
 * Supports per-IP, per-user, or custom key rate limiting.
 */
@injectable()
export class RateLimiter {
  constructor(
    @inject(TYPES.RedisService) private readonly redis: RedisService,
  ) {}

  /**
   * Creates an Express middleware that enforces rate limits.
   * @param options Rate limit configuration
   * @param keyFn Optional function to extract rate limit key from request (default: IP)
   */
  createMiddleware(
    options: RateLimitOptions,
    keyFn?: (req: Request) => string,
  ) {
    const defaultKeyFn = (req: Request): string => {
      return req.ip ?? req.socket.remoteAddress ?? 'unknown';
    };
    const getKey = keyFn ?? defaultKeyFn;

    return async (req: Request, res: Response, next: NextFunction): Promise<void> => {
      const key = `${options.keyPrefix ?? 'ratelimit'}:${options.bucket}:${getKey(req)}`;
      const now = Math.floor(Date.now() / 1000);
      const windowStart = now - options.windowSeconds;

      try {
        const client = this.redis.client;
        const multi = client.multi();

        // Remove expired entries
        multi.zremrangebyscore(key, 0, windowStart);
        // Count current requests in window
        multi.zcard(key);
        // Add current request
        multi.zadd(key, now, `${now}:${Math.random()}`);
        // Set expiry
        multi.expire(key, options.windowSeconds + 1);

        const results = await multi.exec();

        const currentCount = (results?.[1]?.[1] as number) ?? 0;
        const remaining = Math.max(0, options.max - currentCount - 1);
        const reset = now + options.windowSeconds;

        // Set rate limit headers
        res.setHeader('X-RateLimit-Limit', options.max);
        res.setHeader('X-RateLimit-Remaining', remaining);
        res.setHeader('X-RateLimit-Reset', reset);

        if (currentCount >= options.max) {
          const oldest = await client.zrange(key, 0, 0);
          const oldestEntry = oldest?.[0];
          const retryAfter = oldestEntry
            ? Math.max(1, parseInt(oldestEntry.split(':')[0] ?? '0', 10) + options.windowSeconds - now)
            : options.windowSeconds;

          res.setHeader('Retry-After', retryAfter);
          throw new AppError(
            'Rate limit exceeded. Please slow down.',
            429,
            ErrorCode.RATE_LIMITED,
            { details: { retryAfter: [retryAfter.toString()] } },
          );
        }

        next();
      } catch (err) {
        if (err instanceof AppError) throw err;
        // On Redis errors, fail open but log
        console.error('Rate limiter error:', err);
        next();
      }
    };
  }

  /**
   * Get current rate limit info without incrementing.
   */
  async getInfo(key: string, options: RateLimitOptions): Promise<RateLimitInfo> {
    const client = this.redis.client;
    const now = Math.floor(Date.now() / 1000);
    const windowStart = now - options.windowSeconds;

    await client.zremrangebyscore(key, 0, windowStart);
    const count = await client.zcard(key);

    return {
      limit: options.max,
      remaining: Math.max(0, options.max - count),
      reset: now + options.windowSeconds,
    };
  }

  /**
   * Reset rate limit for a specific key.
   */
  async reset(key: string): Promise<void> {
    const client = this.redis.client;
    await client.del(key);
  }
}

/**
 * Create per-IP rate limiter middleware.
 */
export function createRateLimiter(
  redis: RedisService,
  options: RateLimitOptions,
) {
  const limiter = new RateLimiter(redis);
  return limiter.createMiddleware(options);
}

/**
 * Create per-user rate limiter middleware.
 * Falls back to IP if user is not authenticated.
 */
export function createUserRateLimiter(
  redis: RedisService,
  options: RateLimitOptions,
) {
  const limiter = new RateLimiter(redis);
  return limiter.createMiddleware(options, (req) => {
    // Use user ID if authenticated, otherwise IP
    return (req as any).auth?.id ?? req.ip ?? req.socket.remoteAddress ?? 'anonymous';
  });
}

/**
 * Extract user ID for rate limiting, falling back to IP.
 */
export function userKeyFn(req: Request): string {
  return (req as any).auth?.id ?? req.ip ?? req.socket.remoteAddress ?? 'anonymous';
}