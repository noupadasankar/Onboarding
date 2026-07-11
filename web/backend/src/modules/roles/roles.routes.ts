/**
 * Roles routes. Both endpoints require authentication but no specific permission —
 * the role catalog is read-only metadata needed by any authenticated user for
 * dropdown population.
 *
 *   GET /roles        → RoleDTO[]
 *   GET /permissions  → string[]
 */
import { Router, type RequestHandler } from 'express';
import type { Container } from 'inversify';
import { TYPES } from '../../core/di/types';
import { RolesController } from './roles.controller';

export function createRolesRoutes(container: Container, authenticate: RequestHandler): Router {
  const router = Router();
  const controller = container.get<RolesController>(TYPES.RolesController);

  router.get('/roles', authenticate, controller.getRoles);
  router.get('/permissions', authenticate, controller.getPermissions);

  return router;
}
