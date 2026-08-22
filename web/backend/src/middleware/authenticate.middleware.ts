/**
 * Authentication middleware. Verifies the Bearer access token and attaches the
 * principal (id, email, role, derived permissions) to `req.auth`. Permissions are
 * derived from the role via the shared RBAC contract — no DB round-trip.
 *
 * Factory-built so the JwtService is injected (testable, no singletons).
 */
import type { RequestHandler } from 'express';
import { ErrorCode, permissionsForRole } from '@hr-onboarding/shared';
import type { IJwtService } from '../infrastructure/security/jwt.service';
import { UnauthorizedError } from '../core/errors/app-error';
import { asyncHandler } from '../core/http/async-handler';

/** The middleware returned by createAuthenticate. */
export type AuthMiddleware = RequestHandler;

export function createAuthenticate(jwtService: IJwtService): AuthMiddleware {
  return asyncHandler(async (req, _res, next) => {
    const header = req.header('authorization');
    if (!header?.startsWith('Bearer ')) {
      throw new UnauthorizedError('Missing bearer token', ErrorCode.UNAUTHENTICATED);
    }
    const token = header.slice('Bearer '.length).trim();
    const claims = jwtService.verifyAccessToken(token);

    req.auth = {
      id: claims.sub,
      email: claims.email,
      role: claims.role,
      permissions: [...permissionsForRole(claims.role)],
    };
    next();
  });
}
