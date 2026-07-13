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

  router.get('/', authorize(Permission.DOCUMENTS_VIEW), ctrl.list);
  router.get('/:id', authorize(Permission.DOCUMENTS_VIEW), ctrl.getById);
  router.get('/:id/versions', authorize(Permission.DOCUMENTS_VIEW), ctrl.getVersions);
  router.get('/:id/download', authorize(Permission.DOCUMENTS_VIEW), ctrl.download);
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
