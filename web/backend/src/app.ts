/**
 * Express application factory. Defines the middleware order (the request pipeline)
 * and mounts routes + docs + error handling. Pure assembly — no server listen here
 * (that lives in main.ts), which keeps the app importable by integration tests.
 */
import express, { type Express, type Request, type Response } from 'express';
import helmet from 'helmet';
import cors from 'cors';
import type { Container } from 'inversify';
import { TYPES } from './core/di/types';
import type { AppConfig } from './config/env';
import type { Logger } from './core/logging/logger';
import type { PrismaService } from './infrastructure/database/prisma.service';
import type { RedisService } from './infrastructure/cache/redis.service';
import { API_PREFIX } from './config/constants';
import { requestId } from './middleware/request-id.middleware';
import { createRequestLogger } from './middleware/request-logger.middleware';
import { createErrorHandler } from './core/errors/error-handler.middleware';
import { sendFailure } from './core/http/api-response';
import { ErrorCode } from '@optiagent/shared';
import { createApiRouter } from './routes';
import { mountSwagger } from './docs/swagger';

export function createApp(container: Container): Express {
  const config = container.get<AppConfig>(TYPES.Config);
  const logger = container.get<Logger>(TYPES.Logger);
  const prisma = container.get<PrismaService>(TYPES.PrismaService);
  const redis = container.get<RedisService>(TYPES.RedisService);

  const app = express();
  app.disable('x-powered-by');
  app.set('trust proxy', 1);

  // --- Security + parsing ---
  app.use(helmet());
  app.use(
    cors({
      origin: config.corsOrigins,
      credentials: true,
    }),
  );
  app.use(express.json({ limit: '1mb' }));

  // --- Observability ---
  app.use(requestId);
  app.use(createRequestLogger(logger));

  // --- Liveness / readiness ---
  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok', service: 'backend' });
  });
  app.get('/ready', async (_req: Request, res: Response) => {
    const [db, cache] = await Promise.all([prisma.healthCheck(), redis.healthCheck()]);
    const ready = db && cache;
    res.status(ready ? 200 : 503).json({ status: ready ? 'ready' : 'degraded', db, cache });
  });

  // --- API + docs ---
  mountSwagger(app);
  app.use(API_PREFIX, createApiRouter(container));

  // --- 404 + terminal error handler (must be last) ---
  app.use((_req, res) => sendFailure(res, 404, ErrorCode.NOT_FOUND, 'Route not found'));
  app.use(createErrorHandler(logger));

  return app;
}
