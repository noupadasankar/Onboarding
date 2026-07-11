/**
 * Document HTTP controller.
 *
 * GET    /api/v1/documents           — list (paginated, filterable)
 * GET    /api/v1/documents/:id       — get one
 * POST   /api/v1/documents/upload    — multipart upload
 * DELETE /api/v1/documents/:id       — soft-delete
 */
import type { Request, Response } from 'express';
import { inject, injectable } from 'inversify';
import multer from 'multer';
import { TYPES } from '../../core/di/types';
import { asyncHandler } from '../../core/http/async-handler';
import { ApiResponse } from '../../core/http/api-response';
import { AppError } from '../../core/errors/app-error';
import type { IDocumentService } from './application/document.service';

const ALLOWED_MIME = new Set([
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/csv',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
]);

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 50 * 1024 * 1024 }, // 50 MB
  fileFilter: (_req, file, cb) => {
    if (ALLOWED_MIME.has(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new AppError(`Unsupported file type: ${file.mimetype}`, 415));
    }
  },
}).single('file');

@injectable()
export class DocumentController {
  constructor(
    @inject(TYPES.DocumentService) private readonly docs: IDocumentService,
  ) {}

  list = asyncHandler(async (req: Request, res: Response) => {
    const page = Math.max(1, Number(req.query['page'] ?? 1));
    const pageSize = Math.min(100, Math.max(1, Number(req.query['pageSize'] ?? 20)));
    const filters = {
      departmentId: req.query['departmentId'] as string | undefined,
      uploadedById: req.query['uploadedById'] as string | undefined,
    };
    const result = await this.docs.list(page, pageSize, filters);
    ApiResponse.success(res, result);
  });

  getById = asyncHandler(async (req: Request, res: Response) => {
    const doc = await this.docs.getById(req.params['id']!);
    ApiResponse.success(res, doc);
  });

  uploadFile = asyncHandler(async (req: Request, res: Response) => {
    await new Promise<void>((resolve, reject) =>
      upload(req, res, (err) => (err ? reject(err) : resolve())),
    );

    if (!req.file) throw new AppError('No file provided', 400);

    const user = req.auth!;
    const doc = await this.docs.upload({
      buffer: req.file.buffer,
      originalName: req.file.originalname,
      mimeType: req.file.mimetype,
      sizeBytes: req.file.size,
      departmentId: (req.body as Record<string, string>)['departmentId'] ?? null,
      uploadedById: user.id,
      uploadedByRole: user.role,
      uploadedByDept: null,
      requestId: res.locals.requestId,
    });

    ApiResponse.created(res, doc);
  });

  remove = asyncHandler(async (req: Request, res: Response) => {
    await this.docs.delete(req.params['id']!, req.auth!.id);
    ApiResponse.success(res, { deleted: true });
  });
}
