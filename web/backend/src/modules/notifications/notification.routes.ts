/**
 * Notification routes. All routes require authentication.
 *
 * GET    /api/v1/notifications
 * PATCH  /api/v1/notifications/read-all
 * PATCH  /api/v1/notifications/:id/read
 */
import { Router } from 'express';
import type { Container } from 'inversify';
import { TYPES } from '../../core/di/types';
import type { NotificationController } from './notification.controller';
import type { AuthMiddleware } from '../../middleware/authenticate.middleware';

export function createNotificationRoutes(
  container: Container,
  authenticate: AuthMiddleware,
): Router {
  const router = Router();
  const ctrl = container.get<NotificationController>(TYPES.NotificationController);

  router.use(authenticate);

  router.get('/', ctrl.list);
  router.patch('/read-all', ctrl.markAllRead);
  router.patch('/:id/read', ctrl.markRead);

  return router;
}
