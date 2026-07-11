/**
 * Analytics routes.
 *
 * All routes require authentication.
 *
 * GET /api/v1/analytics   — requires Permission.GOVERNANCE_READ
 */
import { Router } from 'express';
import type { Container } from 'inversify';
import { Permission } from '@optiagent/shared';
import { TYPES } from '../../core/di/types';
import { createAuthorize } from '../../middleware/authorize.middleware';
import type { AnalyticsController } from './analytics.controller';
import type { AuthMiddleware } from '../../middleware/authenticate.middleware';

export function createAnalyticsRoutes(
  container: Container,
  authenticate: AuthMiddleware,
): Router {
  const router = Router();
  const ctrl = container.get<AnalyticsController>(TYPES.AnalyticsController);
  const authorize = createAuthorize(container);

  router.use(authenticate);

  router.get('/', authorize(Permission.GOVERNANCE_READ), ctrl.getData);

  return router;
}
