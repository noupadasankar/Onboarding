/**
 * Dashboard routes. All endpoints require authentication; no additional
 * permission gate — any authenticated user may view the dashboard.
 *
 *   GET /dashboard/   → DashboardController.getStats
 */
import { Router } from 'express';
import type { Container } from 'inversify';
import { TYPES } from '../../core/di/types';
import type { AuthMiddleware } from '../../middleware/authenticate.middleware';
import { DashboardController } from './dashboard.controller';

export function createDashboardRoutes(container: Container, authenticate: AuthMiddleware): Router {
  const router = Router();
  const ctrl = container.get<DashboardController>(TYPES.DashboardController);

  router.get('/', authenticate, ctrl.getStats);

  return router;
}
