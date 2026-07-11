/**
 * Owns the shared Redis connection (refresh-token records, blacklist, rate-limit
 * buckets). Thin wrapper exposing the ioredis client + lifecycle + health.
 */
import { inject, injectable } from 'inversify';
import Redis from 'ioredis';
import { TYPES } from '../../core/di/types';
import type { AppConfig } from '../../config/env';
import type { Logger } from '../../core/logging/logger';

@injectable()
export class RedisService {
  readonly client: Redis;

  constructor(
    @inject(TYPES.Config) config: AppConfig,
    @inject(TYPES.Logger) private readonly logger: Logger,
  ) {
    this.client = new Redis(config.redisUrl, {
      lazyConnect: true,
      maxRetriesPerRequest: 2,
    });
    this.client.on('error', (err) => this.logger.error({ err }, 'Redis error'));
  }

  async connect(): Promise<void> {
    await this.client.connect();
    this.logger.info('Redis connected');
  }

  async disconnect(): Promise<void> {
    this.client.disconnect();
    this.logger.info('Redis disconnected');
  }

  async healthCheck(): Promise<boolean> {
    try {
      return (await this.client.ping()) === 'PONG';
    } catch {
      return false;
    }
  }
}
