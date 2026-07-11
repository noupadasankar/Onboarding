/**
 * Department routes.
 *
 * Public (authenticated):
 *   GET /api/v1/departments
 *   GET /api/v1/departments/:id
 *
 * Admin-only (HR_MANAGER / FINANCE_ADMIN / IT_ADMIN):
 *   POST /api/v1/departments
 *   PATCH /api/v1/departments/:id
 */
import { Router } from 'express';
import type { Container } from 'inversify';
import { z } from 'zod';
import { Permission } from '@optiagent/shared';
import { TYPES } from '../../core/di/types';
import { createAuthorize } from '../../middleware/authorize.middleware';
import { validate } from '../../middleware/validate.middleware';
import type { DepartmentController } from './department.controller';
import type { AuthMiddleware } from '../../middleware/authenticate.middleware';

const createBody = z.object({
  name: z.string().min(1).max(64).toLowerCase(),
  displayName: z.string().min(1).max(128),
  description: z.string().max(512).optional(),
});

const updateBody = createBody.partial().extend({
  isActive: z.boolean().optional(),
});

export function createDepartmentRoutes(
  container: Container,
  authenticate: AuthMiddleware,
): Router {
  const router = Router();
  const ctrl = container.get<DepartmentController>(TYPES.DepartmentController);
  const authorize = createAuthorize(container);

  router.use(authenticate);

  router.get('/', ctrl.list);
  router.get('/:id', ctrl.getById);

  router.post(
    '/',
    authorize(Permission.USERS_MANAGE),   // only managers can create departments
    validate({ body: createBody }),
    ctrl.create,
  );

  router.patch(
    '/:id',
    authorize(Permission.USERS_MANAGE),
    validate({ body: updateBody }),
    ctrl.update,
  );

  return router;
}
