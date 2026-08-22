/**
 * API router assembly. Builds the shared middleware that modules need
 * (authenticate, login rate limiter) once, then mounts each feature router under
 * the versioned prefix.
 */
import { Router, type RequestHandler } from 'express';
import type { Container } from 'inversify';
import { TYPES } from '../core/di/types';
import type { AppConfig } from '../config/env';
import type { IJwtService } from '../infrastructure/security/jwt.service';
import type { RedisService } from '../infrastructure/cache/redis.service';
import { createAuthenticate } from '../middleware/authenticate.middleware';
import { createRateLimiter, userKeyFn } from '../middleware/rate-limit.middleware';
import { createAuthRoutes } from '../modules/auth/auth.routes';
import { createUserRoutes } from '../modules/users/user.routes';
import { createRolesRoutes } from '../modules/roles/roles.routes';
import { createDepartmentRoutes } from '../modules/departments/department.routes';
import { createDocumentRoutes } from '../modules/documents/document.routes';
import { createConversationRoutes } from '../modules/conversations/conversation.routes';
import { createDashboardRoutes } from '../modules/dashboard/dashboard.routes';
import { createAnalyticsRoutes } from '../modules/analytics/analytics.routes';
import { createAuditLogsRoutes } from '../modules/audit-logs/audit-logs.routes';
import { createNotificationRoutes } from '../modules/notifications/notification.routes';
import { createAdminSettingsRoutes } from '../modules/admin-settings/admin-settings.routes';
import { TYPES } from '../core/di/types';
import type { OnboardingRoutesFactory } from '../modules/onboarding/application/onboarding.container';

export function createApiRouter(container: Container): Router {
  const router = Router();

  const config = container.get<AppConfig>(TYPES.Config);
  const jwtService = container.get<IJwtService>(TYPES.JwtService);
  const redis = container.get<RedisService>(TYPES.RedisService);

  const authenticate = createAuthenticate(jwtService);

  // Login rate limiter (IP-based)
  const loginRateLimiter = createRateLimiter(redis, {
    bucket: 'login',
    max: config.loginRateLimit.max,
    windowSeconds: config.loginRateLimit.windowSeconds,
  });

  // General write rate limiter (per-user, stricter)
  const writeRateLimiter = createRateLimiter(redis, {
    bucket: 'write',
    max: 60, // 60 writes per minute per user
    windowSeconds: 60,
    keyFn: userKeyFn,
  });

  // Apply write rate limiter to all mutating methods
  const writeMethods: RequestHandler = (req, res, next) => {
    if (['POST', 'PATCH', 'PUT', 'DELETE'].includes(req.method)) {
      return writeRateLimiter(req, res, next);
    }
    next();
  };

  router.use('/auth', createAuthRoutes(container, { authenticate, loginRateLimiter }));
  router.use('/users', authenticate, writeMethods, createUserRoutes(container, authenticate));
  router.use('/', authenticate, writeMethods, createRolesRoutes(container, authenticate));
  router.use('/departments', authenticate, writeMethods, createDepartmentRoutes(container, authenticate));
  router.use('/documents', authenticate, writeMethods, createDocumentRoutes(container, authenticate));
  router.use('/conversations', authenticate, writeMethods, createConversationRoutes(container, authenticate));
  router.use('/dashboard', authenticate, createDashboardRoutes(container, authenticate));
  router.use('/analytics', authenticate, createAnalyticsRoutes(container, authenticate));
  router.use('/audit-logs', authenticate, createAuditLogsRoutes(container, authenticate));
  router.use('/notifications', authenticate, createNotificationRoutes(container, authenticate));
  router.use('/admin/settings', authenticate, writeMethods, createAdminSettingsRoutes(container, authenticate));
  router.use('/onboarding', authenticate, writeMethods, container.get<OnboardingRoutesFactory>(TYPES.OnboardingRoutesFactory)(container, authenticate));

  return router;
}
