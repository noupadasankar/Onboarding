/**
 * Prisma implementation of IDocumentRepository.
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../../core/di/types';
import type { PrismaService } from '../../../infrastructure/database/prisma.service';
import type {
  CreateDocumentInput,
  DocumentDTO,
  DocumentListFilters,
  IDocumentRepository,
  UpdateDocumentStatusInput,
} from '../domain/document.repository';

@injectable()
export class DocumentPrismaRepository implements IDocumentRepository {
  constructor(
    @inject(TYPES.PrismaService) private readonly prisma: PrismaService,
  ) {}

  private map(d: {
    id: string; filename: string; originalName: string; mimeType: string;
    sizeBytes: number; storagePath: string; status: string;
    departmentId: string | null; department: { name: string } | null;
    uploadedById: string; chunkCount: number | null; vectorCount: number | null;
    aiDocumentId: string | null; errorMessage: string | null;
    version: number; isLatest: boolean; parentDocumentId: string | null; supersededAt: Date | null;
    createdAt: Date; updatedAt: Date;
  }): DocumentDTO {
    return {
      id: d.id,
      filename: d.filename,
      originalName: d.originalName,
      mimeType: d.mimeType,
      sizeBytes: d.sizeBytes,
      storagePath: d.storagePath,
      status: d.status as DocumentDTO['status'],
      departmentId: d.departmentId,
      departmentName: d.department?.name ?? null,
      uploadedById: d.uploadedById,
      chunkCount: d.chunkCount,
      vectorCount: d.vectorCount,
      aiDocumentId: d.aiDocumentId,
      errorMessage: d.errorMessage,
      version: d.version,
      isLatest: d.isLatest,
      parentDocumentId: d.parentDocumentId,
      supersededAt: d.supersededAt?.toISOString() ?? null,
      createdAt: d.createdAt.toISOString(),
      updatedAt: d.updatedAt.toISOString(),
    };
  }

  private include = { department: { select: { name: true } } } as const;

  async findAll(page: number, pageSize: number, filters?: DocumentListFilters) {
    // Optional inclusive createdAt range.
    const createdAt =
      filters?.dateFrom || filters?.dateTo
        ? {
            ...(filters?.dateFrom ? { gte: new Date(filters.dateFrom) } : {}),
            ...(filters?.dateTo ? { lte: new Date(filters.dateTo) } : {}),
          }
        : undefined;

    // Optional inclusive size range.
    const sizeBytes =
      filters?.sizeMin != null || filters?.sizeMax != null
        ? {
            ...(filters?.sizeMin != null ? { gte: filters.sizeMin } : {}),
            ...(filters?.sizeMax != null ? { lte: filters.sizeMax } : {}),
          }
        : undefined;

    const where = {
      // When no explicit status is requested, hide superseded and deleted docs
      // (show only the latest active version of each document).
      status: filters?.status
        ? filters.status
        : { notIn: ['DELETED', 'SUPERSEDED'] as ('DELETED' | 'SUPERSEDED')[] },
      isLatest: filters?.status ? undefined : true,
      ...(filters?.departmentId ? { departmentId: filters.departmentId } : {}),
      ...(filters?.uploadedById ? { uploadedById: filters.uploadedById } : {}),
      ...(filters?.filename
        ? { originalName: { contains: filters.filename, mode: 'insensitive' as const } }
        : {}),
      ...(filters?.version != null ? { version: filters.version } : {}),
      ...(filters?.mimeType ? { mimeType: filters.mimeType } : {}),
      ...(createdAt ? { createdAt } : {}),
      ...(sizeBytes ? { sizeBytes } : {}),
    };

    const [total, rows] = await Promise.all([
      this.prisma.client.document.count({ where }),
      this.prisma.client.document.findMany({
        where,
        include: this.include,
        orderBy: { createdAt: 'desc' },
        skip: (page - 1) * pageSize,
        take: pageSize,
      }),
    ]);

    return { items: rows.map((r) => this.map(r)), total, page, pageSize };
  }

  async findById(id: string): Promise<DocumentDTO | null> {
    const row = await this.prisma.client.document.findUnique({
      where: { id },
      include: this.include,
    });
    return row ? this.map(row) : null;
  }

  async create(input: CreateDocumentInput): Promise<DocumentDTO> {
    const row = await this.prisma.client.document.create({
      data: {
        filename: input.filename,
        originalName: input.originalName,
        mimeType: input.mimeType,
        sizeBytes: input.sizeBytes,
        storagePath: input.storagePath,
        departmentId: input.departmentId ?? null,
        uploadedById: input.uploadedById,
        status: 'PENDING',
        version: input.version ?? 1,
        isLatest: input.isLatest ?? true,
        parentDocumentId: input.parentDocumentId ?? null,
      },
      include: this.include,
    });
    return this.map(row);
  }

  async updateStatus(id: string, input: UpdateDocumentStatusInput): Promise<DocumentDTO | null> {
    try {
      const row = await this.prisma.client.document.update({
        where: { id },
        data: {
          status: input.status,
          chunkCount: input.chunkCount ?? undefined,
          vectorCount: input.vectorCount ?? undefined,
          aiDocumentId: input.aiDocumentId ?? undefined,
          errorMessage: input.errorMessage ?? null,
        },
        include: this.include,
      });
      return this.map(row);
    } catch {
      return null;
    }
  }

  async softDelete(id: string): Promise<void> {
    await this.prisma.client.document.update({
      where: { id },
      data: { status: 'DELETED' },
    });
  }

  async findLatestByNameAndDept(
    originalName: string,
    departmentId: string | null,
  ): Promise<DocumentDTO | null> {
    const row = await this.prisma.client.document.findFirst({
      where: {
        originalName,
        departmentId: departmentId ?? null,
        isLatest: true,
        status: { notIn: ['DELETED', 'SUPERSEDED'] },
      },
      include: this.include,
      orderBy: { version: 'desc' },
    });
    return row ? this.map(row) : null;
  }

  async markSuperseded(id: string): Promise<DocumentDTO | null> {
    try {
      const row = await this.prisma.client.document.update({
        where: { id },
        data: {
          status: 'SUPERSEDED',
          isLatest: false,
          supersededAt: new Date(),
        },
        include: this.include,
      });
      return this.map(row);
    } catch {
      return null;
    }
  }

  async findVersions(id: string): Promise<DocumentDTO[]> {
    const doc = await this.prisma.client.document.findUnique({
      where: { id },
      select: { id: true, parentDocumentId: true },
    });
    if (!doc) return [];

    // The root of a version chain is v1: its own id when it has no parent, or the
    // parentDocumentId that every later version points back to.
    const rootId = doc.parentDocumentId ?? doc.id;

    const rows = await this.prisma.client.document.findMany({
      where: {
        OR: [{ id: rootId }, { parentDocumentId: rootId }],
      },
      include: this.include,
      orderBy: { version: 'desc' },
    });
    return rows.map((r) => this.map(r));
  }
}
