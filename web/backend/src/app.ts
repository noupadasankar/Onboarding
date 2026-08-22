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
import { traceContextMiddleware } from './middleware/trace-context.middleware';
import { createRequestLogger } from './middleware/request-logger.middleware';
import { createErrorHandler } from './core/errors/error-handler.middleware';
import { sendFailure } from './core/http/api-response';
import { ErrorCode } from '@hr-onboarding/shared';
import { createApiRouter } from './routes';
import { mountSwagger } from './docs/swagger';

async function checkAiService(url: string): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    const res = await fetch(`${url}/health/live`, { signal: controller.signal });
    clearTimeout(timeout);
    return res.ok;
  } catch {
    return false;
  }
}

function buildHelmetConfig(isProduction: boolean) {
  const base = {
    hidePoweredBy: true,
    frameguard: { action: 'deny' as const },
    hsts: isProduction
      ? { maxAge: 15552000, includeSubDomains: true, preload: true }
      : false,
    referrerPolicy: { policy: 'strict-origin-when-cross-origin' as const },
    noSniff: true,
    xssFilter: true,
    crossOriginEmbedderPolicy: false,
    crossOriginOpenerPolicy: { policy: 'same-origin' as const },
    crossOriginResourcePolicy: { policy: 'same-site' as const },
    contentSecurityPolicy: isProduction
      ? {
          directives: {
            defaultSrc: ["'self'"],
            scriptSrc: ["'self'"],
            styleSrc: ["'self'", "'unsafe-inline'"],
            imgSrc: ["'self'", 'data:', 'blob:'],
            fontSrc: ["'self'"],
            objectSrc: ["'none'"],
            baseUri: ["'self'"],
            formAction: ["'self'"],
            frameAncestors: ["'none'"],
            upgradeInsecureRequests: [],
          },
        }
      : false,
  };
  return base;
}

function buildCorsConfig(corsOrigins: string[], isProduction: boolean) {
  if (isProduction) {
    return {
      origin: corsOrigins,
      credentials: true,
      methods: ['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Request-Id'],
      exposedHeaders: ['X-Request-Id'],
      maxAge: 86400,
      optionsSuccessStatus: 204,
    };
  }
  // Dev: permissive but explicit
  return {
    origin: corsOrigins,
    credentials: true,
    methods: ['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Request-Id'],
    exposedHeaders: ['X-Request-Id'],
    optionsSuccessStatus: 204,
  };
}

export function createApp(container: Container): Express {
  const config = container.get<AppConfig>(TYPES.Config);
  const logger = container.get<Logger>(TYPES.Logger);
  const prisma = container.get<PrismaService>(TYPES.PrismaService);
  const redis = container.get<RedisService>(TYPES.RedisService);

  const app = express();
  app.disable('x-powered-by');
  app.set('trust proxy', 1);

  // --- Security + parsing ---
  app.use(helmet(buildHelmetConfig(config.isProduction)));
  app.use(cors(buildCorsConfig(config.corsOrigins, config.isProduction)));
  app.use(express.json({ limit: '1mb' }));

  // --- Observability ---
  app.use(requestId);
  app.use(traceContextMiddleware);
  app.use(createRequestLogger(logger));

  // --- Liveness / readiness ---
  app.get('/health/live', (_req: Request, res: Response) => {
    res.json({ status: 'alive', service: 'backend', timestamp: new Date().toISOString() });
  });
  app.get('/health/ready', async (_req: Request, res: Response) => {
    const [dbReady, cacheReady, aiReady] = await Promise.all([
      prisma.readinessCheck(),
      redis.readinessCheck?.() ?? redis.healthCheck(),
      checkAiService(config.aiService.url),
    ]);

    const ready = dbReady.ready && cacheReady && aiReady;
    const status = ready ? 200 : 503;

    res.status(status).json({
      status: ready ? 'ready' : 'degraded',
      timestamp: new Date().toISOString(),
      checks: {
        database: { ready: dbReady.ready, ...dbReady.details },
        cache: { ready: cacheReady },
        aiService: { ready: aiReady },
      },
    });
  });
  // Legacy endpoints for backward compatibility
  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok', service: 'backend' });
  });
  app.get('/ready', async (_req: Request, res: Response) => {
    const [db, cache] = await Promise.all([prisma.healthCheck(), redis.healthCheck()]);
    const ready = db && cache;
    res.status(ready ? 200 : 503).json({ status: ready ? 'ready' : 'degraded', db, cache });
  });

  // --- Prometheus metrics endpoint ---
  app.get('/metrics', async (_req: Request, res: Response) => {
    try {
      const promClient = await import('prom-client');
      res.set('Content-Type', promClient.register.contentType);
      res.end(await promClient.register.metrics());
    } catch {
      res.status(500).send('Metrics unavailable');
    }
  });

  // --- API + docs ---
  mountSwagger(app);
  app.use(API_PREFIX, createApiRouter(container));

  // --- 404 + terminal error handler (must be last) ---
  app.use((_req, res) => sendFailure(res, 404, ErrorCode.NOT_FOUND, 'Route not found'));
  app.use(createErrorHandler(logger));

  return app;
}
