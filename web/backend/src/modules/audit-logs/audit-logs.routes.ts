/**
 * Audit logs routes. All routes require authentication. The list endpoint is
 * additionally gated by the USERS_MANAGE permission, since access to audit
 * records is an administrative operation.
 *
 *   GET /audit-logs   requires `users:manage`
 */
import { Router, type RequestHandler } from 'express';
import type { Container } from 'inversify';
import { Permission } from '@optiagent/shared';
import { TYPES } from '../../core/di/types';
import { createAuthorize } from '../../middleware/authorize.middleware';
import { AuditLogViewController } from './audit-logs.controller';

export function createAuditLogsRoutes(container: Container, authenticate: RequestHandler): Router {
  const router = Router();
  const ctrl = container.get<AuditLogViewController>(TYPES.AuditLogViewController);
  const authorize = createAuthorize(container);

  router.get('/', authenticate, authorize(Permission.USERS_MANAGE), ctrl.list);

  return router;
}
