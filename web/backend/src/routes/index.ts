/**
 * API router assembly. Builds the shared middleware that modules need
 * (authenticate, login rate limiter) once, then mounts each feature router under
 * the versioned prefix.
 */
import { Router } from 'express';
import type { Container } from 'inversify';
import { TYPES } from '../core/di/types';
import type { AppConfig } from '../config/env';
import type { IJwtService } from '../infrastructure/security/jwt.service';
import type { RedisService } from '../infrastructure/cache/redis.service';
import { createAuthenticate } from '../middleware/authenticate.middleware';
import { createRateLimiter } from '../middleware/rate-limit.middleware';
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

export function createApiRouter(container: Container): Router {
  const router = Router();

  const config = container.get<AppConfig>(TYPES.Config);
  const jwtService = container.get<IJwtService>(TYPES.JwtService);
  const redis = container.get<RedisService>(TYPES.RedisService);

  const authenticate = createAuthenticate(jwtService);
  const loginRateLimiter = createRateLimiter(redis, {
    bucket: 'login',
    max: config.loginRateLimit.max,
    windowSeconds: config.loginRateLimit.windowSeconds,
  });

  router.use('/auth', createAuthRoutes(container, { authenticate, loginRateLimiter }));
  router.use('/users', createUserRoutes(container, authenticate));
  router.use('/', createRolesRoutes(container, authenticate));
  router.use('/departments', createDepartmentRoutes(container, authenticate));
  router.use('/documents', createDocumentRoutes(container, authenticate));
  router.use('/conversations', createConversationRoutes(container, authenticate));
  router.use('/dashboard', createDashboardRoutes(container, authenticate));
  router.use('/analytics', createAnalyticsRoutes(container, authenticate));
  router.use('/audit-logs', createAuditLogsRoutes(container, authenticate));
  router.use('/notifications', createNotificationRoutes(container, authenticate));
  router.use('/admin/settings', createAdminSettingsRoutes(container, authenticate));

  return router;
}
