/**
 * Document routes.
 *
 * All routes require authentication.
 * Upload requires documents:write permission.
 * Delete requires documents:manage permission.
 */
import { Router, Request, Response, NextFunction } from 'express';
import type { Container } from 'inversify';
import { Permission } from '@hr-onboarding/shared';
import { TYPES } from '../../core/di/types';
import { createAuthorize } from '../../middleware/authorize.middleware';
import type { DocumentController } from './document.controller';
import type { AuthMiddleware } from '../../middleware/authenticate.middleware';
import { sendFailure } from '../../core/http/api-response';
import { ErrorCode } from '@hr-onboarding/shared';

const MAX_UPLOAD_SIZE = 50 * 1024 * 1024; // 50 MB

function uploadSizeLimit(req: Request, res: Response, next: NextFunction): void {
  const contentLength = req.headers['content-length'];
  if (contentLength && parseInt(contentLength, 10) > MAX_UPLOAD_SIZE) {
    return sendFailure(
      res,
      413,
      ErrorCode.PAYLOAD_TOO_LARGE,
      `Upload size exceeds maximum allowed (${MAX_UPLOAD_SIZE / 1024 / 1024} MB)`,
    );
  }
  next();
}

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
    uploadSizeLimit,
    ctrl.uploadFile,
  );
  router.delete(
    '/:id',
    authorize(Permission.DOCUMENTS_MANAGE),
    ctrl.remove,
  );

  return router;
}
