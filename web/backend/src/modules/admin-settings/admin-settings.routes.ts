/**
 * Admin Settings routes. All routes require USERS_MANAGE permission.
 *
 * GET    /api/v1/admin/settings
 * GET    /api/v1/admin/settings/:key
 * PUT    /api/v1/admin/settings/:key
 * DELETE /api/v1/admin/settings/:key
 */
import { Router } from 'express';
import type { Container } from 'inversify';
import { z } from 'zod';
import { Permission } from '@hr-onboarding/shared';
import { TYPES } from '../../core/di/types';
import { createAuthorize } from '../../middleware/authorize.middleware';
import { validate } from '../../middleware/validate.middleware';
import type { AdminSettingsController } from './admin-settings.controller';
import type { AuthMiddleware } from '../../middleware/authenticate.middleware';

const upsertBody = z.object({
  value: z.unknown(),
  description: z.string().max(512).optional(),
});

export function createAdminSettingsRoutes(
  container: Container,
  authenticate: AuthMiddleware,
): Router {
  const router = Router();
  const ctrl = container.get<AdminSettingsController>(TYPES.AdminSettingsController);
  const authorize = createAuthorize(container);

  router.use(authenticate);
  router.use(authorize(Permission.USERS_MANAGE));

  router.get('/', ctrl.listAll);
  router.get('/:key', ctrl.getOne);
  router.put('/:key', validate(upsertBody), ctrl.upsert);
  router.delete('/:key', ctrl.remove);

  return router;
}
