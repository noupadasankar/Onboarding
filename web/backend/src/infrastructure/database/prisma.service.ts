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
    const isProd = config.isProduction;

    this.client = new PrismaClient({
      datasources: { db: { url: config.databaseUrl } },
      log: isProd
        ? ['warn', 'error']
        : [
            { emit: 'event', level: 'query' },
            { emit: 'stdout', level: 'warn' },
            { emit: 'stdout', level: 'error' },
          ],
      errorFormat: 'pretty',
    });

    // Query logging in development (with duration)
    if (!isProd) {
      // @ts-expect-error - Prisma event types not properly exposed
      this.client.$on('query', (e: { query: string; params: string; duration: number }) => {
        this.logger.debug({ query: e.query, durationMs: e.duration }, 'SQL Query');
      });
    }

    // Connection pool monitoring (production)
    if (isProd) {
      setInterval(() => {
        // @ts-expect-error - accessing internal pool for metrics
        const pool = this.client.$pool;
        if (pool) {
          this.logger.debug(
            {
              active: pool.activeConnections,
              idle: pool.idleConnections,
              waiting: pool.waitingClients,
            },
            'PostgreSQL connection pool status',
          );
        }
      }, 30_000);
    }
  }

  async connect(): Promise<void> {
    await this.client.$connect();
    this.logger.info('PostgreSQL connected');
  }

  async disconnect(): Promise<void> {
    await this.client.$disconnect();
    this.logger.info('PostgreSQL disconnected');
  }

  /**
   * Liveness check - simple SELECT 1
   */
  async healthCheck(): Promise<boolean> {
    try {
      await this.client.$queryRaw`SELECT 1`;
      return true;
    } catch (err) {
      this.logger.error({ err }, 'Database health check failed');
      return false;
    }
  }

  /**
   * Readiness check - verifies DB is responsive and migrations are current
   */
  async readinessCheck(): Promise<{ ready: boolean; details: Record<string, unknown> }> {
    const details: Record<string, unknown> = {};

    try {
      // Check connection latency
      const start = Date.now();
      await this.client.$queryRaw`SELECT 1`;
      const latencyMs = Date.now() - start;
      details.latencyMs = latencyMs;

      // Check migration status (count pending)
      const pending = await this.client.$queryRaw<
        Array<{ migration_name: string; finished_at: Date | null }>
      >`
        SELECT migration_name, finished_at
        FROM _prisma_migrations
        WHERE finished_at IS NULL
        ORDER BY migration_name
      `;
      details.pendingMigrations = pending.length;
      details.migrations = pending.map((m) => m.migration_name);

      const ready = pending.length === 0 && latencyMs < 1000;
      return { ready, details };
    } catch (err) {
      this.logger.error({ err }, 'Database readiness check failed');
      return { ready: false, details: { error: String(err) } };
    }
  }

  /**
   * Get connection pool metrics for Prometheus
   */
  getPoolMetrics(): Record<string, number> {
    // @ts-expect-error - accessing internal pool
    const pool = this.client.$pool;
    if (!pool) return {};

    return {
      active: pool.activeConnections,
      idle: pool.idleConnections,
      waiting: pool.waitingClients,
    };
  }
}
