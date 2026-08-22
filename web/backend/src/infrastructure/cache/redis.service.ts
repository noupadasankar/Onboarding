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
      lazyConnect: false,
      maxRetriesPerRequest: null,
    });
    this.client.on('error', (err) => this.logger.error({ err }, 'Redis error'));
  }

  async connect(): Promise<void> {
    if (this.client.status === 'wait') {
      await this.client.connect();
    }
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

  async readinessCheck(): Promise<{ healthy: boolean; latencyMs: number; memory?: string }> {
    const start = Date.now();
    try {
      await this.client.ping();
      const info = await this.client.info('memory');
      const usedMemory = info.match(/used_memory_human:(\S+)/)?.[1];
      return { healthy: true, latencyMs: Date.now() - start, memory: usedMemory };
    } catch {
      return { healthy: false, latencyMs: Date.now() - start };
    }
  }
}
