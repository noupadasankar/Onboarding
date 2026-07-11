/**
 * Auth routes.
 *   POST /auth/login    rate-limited, validated
 *   POST /auth/refresh  validated (rotation happens in the service)
 *   POST /auth/logout   validated
 *   GET  /auth/me       authenticated
 */
import { Router, type RequestHandler } from 'express';
import type { Container } from 'inversify';
import { TYPES } from '../../core/di/types';
import { validate } from '../../middleware/validate.middleware';
import { asyncHandler } from '../../core/http/async-handler';
import { AuthController } from './auth.controller';
import { loginSchema, refreshSchema } from './auth.validators';

export interface AuthRouteDeps {
  authenticate: RequestHandler;
  loginRateLimiter: RequestHandler;
}

export function createAuthRoutes(container: Container, deps: AuthRouteDeps): Router {
  const router = Router();
  const controller = container.get<AuthController>(TYPES.AuthController);

  router.post(
    '/login',
    deps.loginRateLimiter,
    validate(loginSchema),
    asyncHandler(controller.login),
  );

  router.post('/refresh', validate(refreshSchema), asyncHandler(controller.refresh));
  router.post('/logout', validate(refreshSchema), asyncHandler(controller.logout));
  router.get('/me', deps.authenticate, asyncHandler(controller.me));

  return router;
}
