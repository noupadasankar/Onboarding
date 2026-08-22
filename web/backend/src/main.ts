/**
 * Server entrypoint. Loads config, builds the DI container, connects
 * infrastructure, starts Express, and wires graceful shutdown.
 */
import 'reflect-metadata';
import type { Server } from 'node:http';
import { startOtel, stopOtel } from './instrumentation';
import { loadConfig } from './config/env';
import { buildContainer } from './core/di/container';
import { TYPES } from './core/di/types';
import type { Logger } from './core/logging/logger';
import type { PrismaService } from './infrastructure/database/prisma.service';
import type { RedisService } from './infrastructure/cache/redis.service';
import type { IIndexingQueue } from './infrastructure/queue/indexing-queue';
import { createApp } from './app';

async function bootstrap(): Promise<void> {
  // Initialize OpenTelemetry before any other instrumentation
  startOtel();

  const config = loadConfig();
  const container = buildContainer(config);

  const logger = container.get<Logger>(TYPES.Logger);
  const prisma = container.get<PrismaService>(TYPES.PrismaService);
  const redis = container.get<RedisService>(TYPES.RedisService);
  const indexingQueue = container.get<IIndexingQueue>(TYPES.IndexingQueue);

  await prisma.connect();
  await redis.connect();

  const app = createApp(container);
  const server: Server = app.listen(config.port, () => {
    logger.info(`Backend listening on http://localhost:${config.port} (${config.nodeEnv})`);
    logger.info(`Swagger UI at http://localhost:${config.port}/docs`);
  });

  setupGracefulShutdown({ server, prisma, redis, indexingQueue, logger });
}

function setupGracefulShutdown(deps: {
  server: Server;
  prisma: PrismaService;
  redis: RedisService;
  indexingQueue: IIndexingQueue;
  logger: Logger;
}): void {
  const { server, prisma, redis, indexingQueue, logger } = deps;
  let shuttingDown = false;

  const shutdown = async (signal: string): Promise<void> => {
    if (shuttingDown) return;
    shuttingDown = true;
    logger.info(`${signal} received — shutting down`);
    server.close(async () => {
      await Promise.allSettled([
        prisma.disconnect(),
        redis.disconnect(),
        indexingQueue.shutdown(),
        stopOtel(),
      ]);
      process.exit(0);
    });
    // Force-exit if graceful close stalls.
    setTimeout(() => process.exit(1), 10_000).unref();
  };

  process.on('SIGTERM', () => void shutdown('SIGTERM'));
  process.on('SIGINT', () => void shutdown('SIGINT'));
}

bootstrap().catch((err) => {
  // eslint-disable-next-line no-console
  console.error('Fatal startup error:', err);
  process.exit(1);
});
