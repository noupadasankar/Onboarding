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
import { ErrorCode } from '@hr-onboarding/shared';
import type { IDocumentService } from './application/document.service';
import type { DocumentStatus } from './domain/document.repository';

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
      cb(new AppError(`Unsupported file type: ${file.mimetype}`, 415, ErrorCode.VALIDATION));
    }
  },
}).single('file');

@injectable()
export class DocumentController {
  constructor(
    @inject(TYPES.DocumentService) private readonly docs: IDocumentService,
  ) {}

  list = asyncHandler(async (req: Request, res: Response) => {
    const user = req.auth!;
    const q = req.query;
    const page = Math.max(1, Number(q['page'] ?? 1));
    const pageSize = Math.min(100, Math.max(1, Number(q['pageSize'] ?? 20)));
    const num = (v: unknown): number | undefined =>
      v == null || v === '' ? undefined : Number(v);
    // Note: departmentId is intentionally NOT read from the query — the service
    // forces it from the caller's role so params cannot cross departments.
    const filters = {
      uploadedById: q['uploadedById'] as string | undefined,
      status: q['status'] as DocumentStatus | undefined,
      filename: q['filename'] as string | undefined,
      mimeType: q['mimeType'] as string | undefined,
      dateFrom: q['dateFrom'] as string | undefined,
      dateTo: q['dateTo'] as string | undefined,
      version: num(q['version']),
      sizeMin: num(q['sizeMin']),
      sizeMax: num(q['sizeMax']),
    };
    const result = await this.docs.list(user.role, page, pageSize, filters);
    ApiResponse.success(res, result);
  });

  getById = asyncHandler(async (req: Request, res: Response) => {
    const doc = await this.docs.getById(req.params['id']!, req.auth!.role);
    ApiResponse.success(res, doc);
  });

  getVersions = asyncHandler(async (req: Request, res: Response) => {
    const versions = await this.docs.getVersions(req.params['id']!, req.auth!.role);
    ApiResponse.success(res, { items: versions });
  });

  download = asyncHandler(async (req: Request, res: Response) => {
    const user = req.auth!;
    const { buffer, filename, mimeType } = await this.docs.download(
      req.params['id']!,
      user.id,
      user.role,
      res.locals.requestId,
    );
    res.setHeader('Content-Type', mimeType);
    res.setHeader(
      'Content-Disposition',
      `attachment; filename="${encodeURIComponent(filename)}"`,
    );
    res.send(buffer);
  });

  uploadFile = asyncHandler(async (req: Request, res: Response) => {
    await new Promise<void>((resolve, reject) =>
      upload(req, res, (err) => (err ? reject(err) : resolve())),
    );

    if (!req.file) throw new AppError('No file provided', 400, ErrorCode.VALIDATION);

    const user = req.auth!;
    // departmentId is derived from the uploader's role inside the service — any
    // value in the request body is ignored on purpose.
    const doc = await this.docs.upload({
      buffer: req.file.buffer,
      originalName: req.file.originalname,
      mimeType: req.file.mimetype,
      sizeBytes: req.file.size,
      uploadedById: user.id,
      uploadedByRole: user.role,
      requestId: res.locals.requestId,
    });

    ApiResponse.created(res, doc);
  });

  remove = asyncHandler(async (req: Request, res: Response) => {
    const user = req.auth!;
    await this.docs.delete(req.params['id']!, user.id, user.role);
    ApiResponse.success(res, { deleted: true });
  });
}
