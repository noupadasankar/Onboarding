/**
 * Document application service.
 *
 * Orchestrates: upload → store metadata → trigger AI indexing (async).
 */
import { inject, injectable } from 'inversify';
import { join } from 'node:path';
import { mkdir, writeFile } from 'node:fs/promises';
import { TYPES } from '../../../core/di/types';
import { NotFoundError, ForbiddenError } from '../../../core/errors/app-error';
import type { IAuditLogService } from '../../../infrastructure/audit/audit-log.service';
import type { IAiGateway } from '../../../infrastructure/ai/ai-gateway';
import type {
  DocumentDTO,
  DocumentListFilters,
  IDocumentRepository,
} from '../domain/document.repository';
import type { Logger } from 'pino';
import type { AppConfig } from '../../../config/env';

export interface UploadFileInput {
  buffer: Buffer;
  originalName: string;
  mimeType: string;
  sizeBytes: number;
  departmentId?: string | null;
  uploadedById: string;
  uploadedByRole: string;
  uploadedByDept?: string | null;
  requestId?: string;
}

export interface IDocumentService {
  list(page: number, pageSize: number, filters?: DocumentListFilters): Promise<{
    items: DocumentDTO[];
    total: number;
    page: number;
    pageSize: number;
  }>;
  getById(id: string): Promise<DocumentDTO>;
  upload(input: UploadFileInput): Promise<DocumentDTO>;
  delete(id: string, actorId: string): Promise<void>;
}

@injectable()
export class DocumentService implements IDocumentService {
  /** Base directory for uploaded files — in production replace with S3. */
  private readonly uploadDir: string;

  constructor(
    @inject(TYPES.DocumentRepository) private readonly repo: IDocumentRepository,
    @inject(TYPES.AiGateway) private readonly ai: IAiGateway,
    @inject(TYPES.AuditLogService) private readonly audit: IAuditLogService,
    @inject(TYPES.Logger) private readonly log: Logger,
    @inject(TYPES.Config) config: AppConfig,
  ) {
    // Could be pulled from config; for now derive from CWD.
    void config; // accessed via constructor for DI wiring
    this.uploadDir = join(process.cwd(), 'uploads');
  }

  async list(page: number, pageSize: number, filters?: DocumentListFilters) {
    return this.repo.findAll(page, pageSize, filters);
  }

  async getById(id: string): Promise<DocumentDTO> {
    const doc = await this.repo.findById(id);
    if (!doc) throw new NotFoundError('Document not found');
    return doc;
  }

  async upload(input: UploadFileInput): Promise<DocumentDTO> {
    // 1. Persist file to local disk (replace with S3 put in production).
    const safeFilename = `${Date.now()}-${input.originalName.replace(/[^\w.-]/g, '_')}`;
    const storagePath = join(this.uploadDir, safeFilename);
    await mkdir(this.uploadDir, { recursive: true });
    await writeFile(storagePath, input.buffer);

    // 2. Check for an existing latest version of the same document name in this
    //    department. If found, bump the version number, mark the old one superseded,
    //    and schedule deletion of its ChromaDB vectors (both fire-and-forget).
    const existing = await this.repo.findLatestByNameAndDept(
      input.originalName,
      input.departmentId ?? null,
    );

    let version = 1;
    let parentDocumentId: string | null = null;

    if (existing) {
      version = existing.version + 1;
      parentDocumentId = existing.parentDocumentId ?? existing.id;

      this.repo.markSuperseded(existing.id).catch((err: Error) => {
        this.log.error(
          { document_id: existing.id, error: err.message },
          'document:supersede_failed',
        );
      });

      this._deleteVectorsAsync(existing.id).catch((err: Error) => {
        this.log.warn(
          { document_id: existing.id, error: err.message },
          'document:delete_vectors_warn',
        );
      });

      this.log.info(
        { previous_id: existing.id, new_version: version, filename: input.originalName },
        'document:new_version_detected',
      );
    }

    // 3. Create DB record (status = PENDING).
    const doc = await this.repo.create({
      filename: safeFilename,
      originalName: input.originalName,
      mimeType: input.mimeType,
      sizeBytes: input.sizeBytes,
      storagePath,
      departmentId: input.departmentId ?? null,
      uploadedById: input.uploadedById,
      version,
      parentDocumentId,
    });

    this.log.info({ document_id: doc.id, filename: safeFilename }, 'document:uploaded');

    await this.audit.log({
      userId: input.uploadedById,
      action: 'DOCUMENT_UPLOADED',
      resource: `documents/${doc.id}`,
      metadata: { filename: input.originalName, mimeType: input.mimeType, sizeBytes: input.sizeBytes },
      requestId: input.requestId,
    });

    // 3. Kick off AI indexing asynchronously — don't block the HTTP response.
    this._indexAsync(doc, input).catch((err: Error) => {
      this.log.error({ document_id: doc.id, error: err.message }, 'document:index_async_failed');
    });

    return doc;
  }

  async delete(id: string, actorId: string): Promise<void> {
    const doc = await this.repo.findById(id);
    if (!doc) throw new NotFoundError('Document not found');

    await this.repo.softDelete(id);
    await this.audit.log({
      userId: actorId,
      action: 'DOCUMENT_DELETED',
      resource: `documents/${id}`,
    });
  }

  /** Fire-and-forget: delete all ChromaDB vectors for a superseded document. */
  private async _deleteVectorsAsync(documentId: string): Promise<void> {
    try {
      await this.ai.deleteDocumentVectors(documentId);
      this.log.info({ document_id: documentId }, 'document:vectors_deleted');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      // Non-fatal — superseded record in Postgres prevents it from appearing
      // in the document list; stale vectors will not be retrieved for INDEXED docs.
      this.log.warn({ document_id: documentId, error: msg }, 'document:vectors_delete_failed');
    }
  }

  /** Fire-and-forget: set status INDEXING, call AI service, update result. */
  private async _indexAsync(doc: DocumentDTO, ctx: UploadFileInput): Promise<void> {
    await this.repo.updateStatus(doc.id, { status: 'INDEXING' });

    try {
      const result = await this.ai.indexDocument(
        {
          document_id: doc.id,
          filename: doc.filename,
          storage_path: doc.storagePath,
          department: doc.departmentName,
          mime_type: doc.mimeType,
          size_bytes: doc.sizeBytes,
        },
        {
          userId: ctx.uploadedById,
          role: ctx.uploadedByRole,
          department: ctx.uploadedByDept ?? null,
        },
      );

      await this.repo.updateStatus(doc.id, {
        status: 'INDEXED',
        chunkCount: result.chunk_count ?? null,
        vectorCount: result.vector_count ?? null,
        aiDocumentId: result.ai_document_id ?? null,
      });

      this.log.info(
        { document_id: doc.id, chunks: result.chunk_count },
        'document:indexed',
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      await this.repo.updateStatus(doc.id, { status: 'FAILED', errorMessage: msg });
      this.log.error({ document_id: doc.id, error: msg }, 'document:index_failed');
    }
  }
}
