/**
 * Document routes.
 *
 * All routes require authentication.
 * Upload requires documents:write permission.
 * Delete requires documents:manage permission.
 */
import { Router } from 'express';
import type { Container } from 'inversify';
import { Permission } from '@optiagent/shared';
import { TYPES } from '../../core/di/types';
import { createAuthorize } from '../../middleware/authorize.middleware';
import type { DocumentController } from './document.controller';
import type { AuthMiddleware } from '../../middleware/authenticate.middleware';

export function createDocumentRoutes(
  container: Container,
  authenticate: AuthMiddleware,
): Router {
  const router = Router();
  const ctrl = container.get<DocumentController>(TYPES.DocumentController);
  const authorize = createAuthorize(container);

  router.use(authenticate);

  router.get('/', ctrl.list);
  router.get('/:id', ctrl.getById);
  router.post(
    '/upload',
    authorize(Permission.DOCUMENTS_UPLOAD),
    ctrl.uploadFile,
  );
  router.delete(
    '/:id',
    authorize(Permission.DOCUMENTS_MANAGE),
    ctrl.remove,
  );

  return router;
}
