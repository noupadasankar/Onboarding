/**
 * Document application service.
 *
 * Orchestrates: upload → store metadata → trigger AI indexing (async).
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../../core/di/types';
import { ForbiddenError, NotFoundError } from '../../../core/errors/app-error';
import type { IAuditLogService } from '../../../infrastructure/audit/audit-log.service';
import type { IAiGateway } from '../../../infrastructure/ai/ai-gateway';
import type { IStorageService } from '../../../infrastructure/storage/storage.service';
import type {
  IIndexingQueue,
  IndexingJob,
  JobAttempt,
} from '../../../infrastructure/queue/indexing-queue';
import type { IDepartmentAccessService } from '../../../core/auth/department-access.service';
import type { IDepartmentRepository } from '../../departments/domain/department.repository';
import type { INotificationService } from '../../notifications/application/notification.service';
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
  uploadedById: string;
  uploadedByRole: string;
  requestId?: string;
}

export interface IDocumentService {
  /**
   * List documents scoped to the caller's role. The department filter is derived
   * from `role` and always overrides any client-supplied departmentId, so a
   * changed query parameter can never widen scope beyond the caller's department.
   */
  list(
    role: string,
    page: number,
    pageSize: number,
    filters?: DocumentListFilters,
  ): Promise<{
    items: DocumentDTO[];
    total: number;
    page: number;
    pageSize: number;
  }>;
  /** Fetch one document, rejecting cross-department access with 403. */
  getById(id: string, role: string): Promise<DocumentDTO>;
  upload(input: UploadFileInput): Promise<DocumentDTO>;
  /** Soft-delete a document the caller's department owns (403 otherwise). */
  delete(id: string, actorId: string, role: string): Promise<void>;
  /** Return the file bytes + metadata for download (dept-scoped, 403 otherwise). */
  download(
    id: string,
    actorId: string,
    role: string,
    requestId?: string,
  ): Promise<{ buffer: Buffer; filename: string; mimeType: string }>;
  /** Return the version chain for a document (dept-scoped). */
  getVersions(id: string, role: string): Promise<DocumentDTO[]>;
}

@injectable()
export class DocumentService implements IDocumentService {
  /**
   * Cache of canonical department name → UUID. Departments are seed-time
   * immutable, so an in-process map avoids a DB round-trip on every request.
   */
  private readonly deptIdCache = new Map<string, string | null>();

  constructor(
    @inject(TYPES.DocumentRepository) private readonly repo: IDocumentRepository,
    @inject(TYPES.AiGateway) private readonly ai: IAiGateway,
    @inject(TYPES.AuditLogService) private readonly audit: IAuditLogService,
    @inject(TYPES.StorageService) private readonly storage: IStorageService,
    @inject(TYPES.IndexingQueue) private readonly queue: IIndexingQueue,
    @inject(TYPES.NotificationService)
    private readonly notifications: INotificationService,
    @inject(TYPES.DepartmentAccessService)
    private readonly access: IDepartmentAccessService,
    @inject(TYPES.DepartmentRepository)
    private readonly deptRepo: IDepartmentRepository,
    @inject(TYPES.Logger) private readonly log: Logger,
    @inject(TYPES.Config) config: AppConfig,
  ) {
    void config; // accessed via constructor for DI wiring
    // Register the indexing worker once. The queue drains jobs with bounded
    // concurrency and retries; the handler owns all status transitions.
    this.queue.process((job, ctx) => this._handleIndexingJob(job, ctx));
  }

  /** Resolve a canonical department name to its Postgres UUID (memoized). */
  private async departmentIdForName(name: string | null): Promise<string | null> {
    if (!name) return null;
    if (this.deptIdCache.has(name)) return this.deptIdCache.get(name) ?? null;
    const dept = await this.deptRepo.findByName(name);
    const id = dept?.id ?? null;
    this.deptIdCache.set(name, id);
    return id;
  }

  async list(
    role: string,
    page: number,
    pageSize: number,
    filters?: DocumentListFilters,
  ) {
    // Force the department scope from the caller's role. A client-supplied
    // departmentId is intentionally ignored so params cannot cross departments.
    const deptName = this.access.getDepartmentForRole(role);
    const departmentId = (await this.departmentIdForName(deptName)) ?? undefined;
    return this.repo.findAll(page, pageSize, { ...filters, departmentId });
  }

  async getById(id: string, role: string): Promise<DocumentDTO> {
    const doc = await this.repo.findById(id);
    if (!doc) throw new NotFoundError('Document not found');
    if (!this.access.canAccessDepartment(role, doc.departmentName)) {
      throw new ForbiddenError('You do not have access to this document');
    }
    return doc;
  }

  async upload(input: UploadFileInput): Promise<DocumentDTO> {
    // 0. Department is derived from the uploader's role — NEVER from the client.
    //    This guarantees an HR manager's upload always lands in HR regardless of
    //    any departmentId in the request body.
    if (!this.access.canUpload(input.uploadedByRole)) {
      throw new ForbiddenError('Your role cannot upload documents');
    }
    const deptName = this.access.getDepartmentForRole(input.uploadedByRole);
    const departmentId = await this.departmentIdForName(deptName);

    // 1. Persist file via the storage abstraction (local disk today; a one-line
    //    DI swap moves this to S3/Azure/MinIO). Files are foldered by department.
    const saved = await this.storage.save({
      department: deptName ?? 'general',
      originalName: input.originalName,
      buffer: input.buffer,
    });
    const safeFilename = saved.filename;
    const storagePath = saved.storagePath;

    // 2. Check for an existing latest version of the same document name in this
    //    department. If found, bump the version number, mark the old one superseded,
    //    and schedule deletion of its ChromaDB vectors (both fire-and-forget).
    const existing = await this.repo.findLatestByNameAndDept(
      input.originalName,
      departmentId,
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

      this._deleteVectorsAsync(existing.id, input.uploadedById, deptName, input.requestId).catch(
        (err: Error) => {
          this.log.warn(
            { document_id: existing.id, error: err.message },
            'document:delete_vectors_warn',
          );
        },
      );

      // Audit the supersede with the full version transition for history.
      await this.audit.log({
        userId: input.uploadedById,
        action: 'DOCUMENT_SUPERSEDED',
        resource: `documents/${existing.id}`,
        metadata: {
          filename: input.originalName,
          department: deptName,
          old_version: existing.version,
          new_version: version,
          storagePath: existing.storagePath,
        },
        requestId: input.requestId,
      });

      // Notify the previous uploader that a newer version now supersedes theirs.
      await this._safeNotify({
        userId: existing.uploadedById,
        type: 'document_superseded',
        title: 'Document superseded',
        body: `A new version (v${version}) of "${input.originalName}" was uploaded.`,
        metadata: { documentId: existing.id, filename: input.originalName, version },
      });

      this.log.info(
        { previous_id: existing.id, new_version: version, filename: input.originalName },
        'document:new_version_detected',
      );
    }

    // 3. Create DB record (status = PENDING) under the role-derived department.
    const doc = await this.repo.create({
      filename: safeFilename,
      originalName: input.originalName,
      mimeType: input.mimeType,
      sizeBytes: input.sizeBytes,
      storagePath,
      departmentId,
      uploadedById: input.uploadedById,
      version,
      parentDocumentId,
    });

    this.log.info({ document_id: doc.id, filename: safeFilename }, 'document:uploaded');

    await this.audit.log({
      userId: input.uploadedById,
      action: 'DOCUMENT_UPLOADED',
      resource: `documents/${doc.id}`,
      metadata: {
        filename: input.originalName,
        department: deptName,
        version,
        mimeType: input.mimeType,
        sizeBytes: input.sizeBytes,
        storagePath,
      },
      requestId: input.requestId,
    });

    // 4. Enqueue AI indexing — the worker drains the queue with bounded
    //    concurrency and retries, so the HTTP response is never blocked and a
    //    burst of uploads cannot overwhelm the AI service.
    this.queue.enqueue({
      documentId: doc.id,
      uploadedById: input.uploadedById,
      uploadedByRole: input.uploadedByRole,
    });

    return doc;
  }

  async delete(id: string, actorId: string, role: string): Promise<void> {
    const doc = await this.repo.findById(id);
    if (!doc) throw new NotFoundError('Document not found');
    if (!this.access.canAccessDepartment(role, doc.departmentName)) {
      throw new ForbiddenError('You do not have access to this document');
    }

    // Soft-delete in Postgres (status = DELETED) …
    await this.repo.softDelete(id);
    await this.audit.log({
      userId: actorId,
      action: 'DOCUMENT_DELETED',
      resource: `documents/${id}`,
      metadata: {
        filename: doc.originalName,
        department: doc.departmentName,
        version: doc.version,
        storagePath: doc.storagePath,
      },
    });

    // … and remove its ChromaDB vectors so deleted content is never retrieved.
    await this._deleteVectorsAsync(id, actorId, doc.departmentName);

    // Notify the uploader that their document was removed.
    await this._safeNotify({
      userId: doc.uploadedById,
      type: 'document_deleted',
      title: 'Document deleted',
      body: `"${doc.originalName}" was deleted.`,
      metadata: { documentId: id, filename: doc.originalName },
    });
  }

  async download(
    id: string,
    actorId: string,
    role: string,
    requestId?: string,
  ): Promise<{ buffer: Buffer; filename: string; mimeType: string }> {
    // getById enforces existence + department access (403 on cross-department).
    const doc = await this.getById(id, role);

    const buffer = await this.storage.download(doc.storagePath);

    await this.audit.log({
      userId: actorId,
      action: 'DOCUMENT_DOWNLOADED',
      resource: `documents/${id}`,
      metadata: {
        filename: doc.originalName,
        department: doc.departmentName,
        version: doc.version,
      },
      requestId,
    });

    return { buffer, filename: doc.originalName, mimeType: doc.mimeType };
  }

  async getVersions(id: string, role: string): Promise<DocumentDTO[]> {
    // Enforce department access on the anchor document before exposing history.
    await this.getById(id, role);
    return this.repo.findVersions(id);
  }

  /**
   * Delete all ChromaDB vectors for a document (on supersede or explicit delete)
   * and audit the vector deletion. Non-fatal: a failure is logged but does not
   * roll back the Postgres state that already hides the document.
   */
  private async _deleteVectorsAsync(
    documentId: string,
    actorId?: string,
    department?: string | null,
    requestId?: string,
  ): Promise<void> {
    try {
      const { vectors_deleted } = await this.ai.deleteDocumentVectors(documentId);
      this.log.info({ document_id: documentId, vectors_deleted }, 'document:vectors_deleted');
      await this.audit.log({
        userId: actorId,
        action: 'DOCUMENT_VECTORS_DELETED',
        resource: `documents/${documentId}`,
        metadata: { department: department ?? null, vectorsDeleted: vectors_deleted },
        requestId,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      // Non-fatal — superseded/deleted record in Postgres prevents it from
      // appearing in the document list; is_latest filtering also hides stale vectors.
      this.log.warn({ document_id: documentId, error: msg }, 'document:vectors_delete_failed');
    }
  }

  /** Create a notification, swallowing any error so it never breaks the flow. */
  private async _safeNotify(input: {
    userId: string;
    type: string;
    title: string;
    body: string;
    metadata?: Record<string, unknown>;
  }): Promise<void> {
    try {
      await this.notifications.notify(input);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      this.log.warn({ user_id: input.userId, type: input.type, error: msg }, 'document:notify_failed');
    }
  }

  /**
   * Queue worker: set status INDEXING, call the AI service, persist the result.
   *
   * On failure it rethrows so the queue can retry with backoff; the terminal
   * FAILED status is only written on the final attempt so a transient error does
   * not prematurely mark the document as failed.
   */
  private async _handleIndexingJob(job: IndexingJob, ctx: JobAttempt): Promise<void> {
    const doc = await this.repo.findById(job.documentId);
    if (!doc) {
      // Document was deleted before indexing ran — nothing to do.
      this.log.warn({ document_id: job.documentId }, 'document:index_skipped_missing');
      return;
    }

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
          // The document being indexed is always the current latest version.
          version: doc.version,
          is_latest: true,
          // Provenance for vector metadata (traceability + future filtering).
          department_id: doc.departmentId,
          uploaded_by: doc.uploadedById,
          uploaded_at: doc.createdAt,
          document_status: 'INDEXED',
        },
        {
          userId: job.uploadedById,
          role: job.uploadedByRole,
          // Canonical department the document was stored under (role-derived).
          department: doc.departmentName,
        },
      );

      await this.repo.updateStatus(doc.id, {
        status: 'INDEXED',
        chunkCount: result.chunk_count ?? null,
        vectorCount: result.vector_count ?? null,
        aiDocumentId: result.ai_document_id ?? null,
      });

      this.log.info(
        { document_id: doc.id, chunks: result.chunk_count, attempt: ctx.attempt },
        'document:indexed',
      );

      await this.audit.log({
        userId: doc.uploadedById,
        action: 'DOCUMENT_INDEX_SUCCEEDED',
        resource: `documents/${doc.id}`,
        metadata: {
          filename: doc.originalName,
          department: doc.departmentName,
          version: doc.version,
          chunkCount: result.chunk_count ?? null,
          vectorCount: result.vector_count ?? null,
        },
      });

      await this._safeNotify({
        userId: doc.uploadedById,
        type: 'document_indexed',
        title: 'Document indexed successfully',
        body: `"${doc.originalName}" is now searchable by the assistant.`,
        metadata: { documentId: doc.id, filename: doc.originalName, version: doc.version },
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (ctx.isFinalAttempt) {
        // Give up: persist a terminal FAILED status with the last error.
        await this.repo.updateStatus(doc.id, { status: 'FAILED', errorMessage: msg });
        this.log.error(
          { document_id: doc.id, attempt: ctx.attempt, error: msg },
          'document:index_failed',
        );

        await this.audit.log({
          userId: doc.uploadedById,
          action: 'DOCUMENT_INDEX_FAILED',
          resource: `documents/${doc.id}`,
          metadata: {
            filename: doc.originalName,
            department: doc.departmentName,
            version: doc.version,
            error: msg,
          },
        });

        await this._safeNotify({
          userId: doc.uploadedById,
          type: 'document_failed',
          title: 'Document indexing failed',
          body: `"${doc.originalName}" could not be indexed. Please try re-uploading.`,
          metadata: { documentId: doc.id, filename: doc.originalName, error: msg },
        });
      } else {
        // Leave status as INDEXING and rethrow so the queue retries with backoff.
        this.log.warn(
          { document_id: doc.id, attempt: ctx.attempt, error: msg },
          'document:index_attempt_failed',
        );
      }
      // Rethrow drives the queue's retry/backoff (no-op after final attempt).
      throw err;
    }
  }
}
