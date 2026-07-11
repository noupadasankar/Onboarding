/**
 * Refresh-token store (Redis) — the authority for which refresh tokens are still
 * active. Enables rotation (revoke old jti, store new) and immediate logout
 * invalidation (a blacklisted/absent jti fails verification).
 *
 * Redis holds the fast active-set keyed by jti with a TTL matching the token.
 * The Prisma `RefreshToken` table is the durable audit companion, wired in a
 * later increment; the security decision itself lives here for O(1) checks.
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../core/di/types';
import type { RedisService } from '../cache/redis.service';

export interface ITokenStore {
  /** Record a newly issued refresh token as active. */
  store(jti: string, userId: string, ttlSeconds: number): Promise<void>;
  /** True while the refresh token is still active (not rotated/revoked/expired). */
  isActive(jti: string): Promise<boolean>;
  /** Revoke a single refresh token (rotation or logout). */
  revoke(jti: string): Promise<void>;
}

const key = (jti: string): string => `refresh:${jti}`;

@injectable()
export class RedisTokenStore implements ITokenStore {
  constructor(@inject(TYPES.RedisService) private readonly redis: RedisService) {}

  async store(jti: string, userId: string, ttlSeconds: number): Promise<void> {
    await this.redis.client.set(key(jti), userId, 'EX', ttlSeconds);
  }

  async isActive(jti: string): Promise<boolean> {
    return (await this.redis.client.exists(key(jti))) === 1;
  }

  async revoke(jti: string): Promise<void> {
    await this.redis.client.del(key(jti));
  }
}
