/**
 * Users routes. Composes the middleware chain (authenticate → authorize → validate)
 * and delegates to the controller resolved from the DI container.
 *
 *   GET    /users/me       any authenticated principal
 *   GET    /users          requires `users:read`
 *   GET    /users/:id      requires `users:read`
 *   POST   /users          requires `users:write`
 *   PATCH  /users/:id      requires `users:write`
 *   DELETE /users/:id      requires `users:write`  (soft-deactivate)
 */
import { Router, type RequestHandler } from 'express';
import type { Container } from 'inversify';
import { Permission } from '@optiagent/shared';
import { TYPES } from '../../core/di/types';
import { requirePermission } from '../../middleware/authorize.middleware';
import { validate } from '../../middleware/validate.middleware';
import { asyncHandler } from '../../core/http/async-handler';
import { UserController } from './user.controller';
import {
  createUserSchema,
  updateUserSchema,
  userListQuerySchema,
  uuidParamSchema,
} from './user.validators';

export function createUserRoutes(container: Container, authenticate: RequestHandler): Router {
  const router = Router();
  const controller = container.get<UserController>(TYPES.UserController);

  // /me must be registered before /:id to prevent "me" matching the param pattern.
  router.get('/me', authenticate, asyncHandler(controller.me));

  router.get(
    '/',
    authenticate,
    requirePermission(Permission.USERS_READ),
    validate(userListQuerySchema, 'query'),
    asyncHandler(controller.list),
  );

  router.get(
    '/:id',
    authenticate,
    requirePermission(Permission.USERS_READ),
    validate(uuidParamSchema, 'params'),
    asyncHandler(controller.getById),
  );

  router.post(
    '/',
    authenticate,
    requirePermission(Permission.USERS_WRITE),
    validate(createUserSchema, 'body'),
    asyncHandler(controller.create),
  );

  router.patch(
    '/:id',
    authenticate,
    requirePermission(Permission.USERS_WRITE),
    validate(uuidParamSchema, 'params'),
    validate(updateUserSchema, 'body'),
    asyncHandler(controller.update),
  );

  router.delete(
    '/:id',
    authenticate,
    requirePermission(Permission.USERS_WRITE),
    validate(uuidParamSchema, 'params'),
    asyncHandler(controller.deactivate),
  );

  return router;
}
