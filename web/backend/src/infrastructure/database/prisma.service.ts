/**
 * Owns the single PrismaClient instance for the process. Injected wherever DB
 * access is needed (repositories only). Composition over inheritance keeps the
 * class DI-friendly and easy to mock.
 */
import { inject, injectable } from 'inversify';
import { PrismaClient } from '@prisma/client';
import { TYPES } from '../../core/di/types';
import type { AppConfig } from '../../config/env';
import type { Logger } from '../../core/logging/logger';

@injectable()
export class PrismaService {
  readonly client: PrismaClient;

  constructor(
    @inject(TYPES.Config) config: AppConfig,
    @inject(TYPES.Logger) private readonly logger: Logger,
  ) {
    this.client = new PrismaClient({
      datasources: { db: { url: config.databaseUrl } },
      log: config.isProduction ? ['warn', 'error'] : ['warn', 'error'],
    });
  }

  async connect(): Promise<void> {
    await this.client.$connect();
    this.logger.info('PostgreSQL connected');
  }

  async disconnect(): Promise<void> {
    await this.client.$disconnect();
    this.logger.info('PostgreSQL disconnected');
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.client.$queryRaw`SELECT 1`;
      return true;
    } catch {
      return false;
    }
  }
}
