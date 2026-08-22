/**
 * Authorization middleware (RBAC). requirePermission returns a guard that
 * admits a request only if the authenticated principal holds the permission.
 * Must run after authenticate. This is the single choke point for access
 * decisions — controllers never check permissions themselves.
 */
import type { RequestHandler } from 'express';
import type { Container } from 'inversify';
import type { Permission } from '@hr-onboarding/shared';
import { ForbiddenError, UnauthorizedError } from '../core/errors/app-error';

export function requirePermission(...required: Permission[]): RequestHandler {
  return (req, _res, next) => {
    if (!req.auth) {
      next(new UnauthorizedError());
      return;
    }
    const granted = new Set(req.auth.permissions);
    const ok = required.every((p) => granted.has(p));
    next(ok ? undefined : new ForbiddenError('Insufficient permissions'));
  };
}

/** Factory wrapper — accepts container for future extensibility (e.g. dynamic ABAC). */
export function createAuthorize(_container: Container) {
  return (...required: Permission[]): RequestHandler => requirePermission(...required);
}
