/**
 * Audit log READ service. Provides paginated, filterable access to the AuditLog
 * table for administrative review. This is entirely separate from the write-side
 * AuditLogService (TYPES.AuditLogService) — it does not modify any records.
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../core/di/types';
import type { PrismaService } from '../../infrastructure/database/prisma.service';

export type AuditLogEntry = {
  id: string;
  userId: string | null;
  userEmail: string | null;
  action: string;
  resource: string | null;
  metadata: unknown;
  ipAddress: string | null;
  requestId: string | null;
  createdAt: Date;
};

export type AuditLogPage = {
  items: AuditLogEntry[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export interface IAuditLogViewService {
  list(opts: {
    page: number;
    pageSize: number;
    userId?: string;
    action?: string;
    from?: Date;
    to?: Date;
  }): Promise<AuditLogPage>;
}

@injectable()
export class AuditLogViewService implements IAuditLogViewService {
  constructor(
    @inject(TYPES.PrismaService) private readonly prisma: PrismaService,
  ) {}

  async list(opts: {
    page: number;
    pageSize: number;
    userId?: string;
    action?: string;
    from?: Date;
    to?: Date;
  }): Promise<AuditLogPage> {
    const { page, pageSize, userId, action, from, to } = opts;

    const where: Record<string, unknown> = {};

    if (userId) {
      where['userId'] = userId;
    }

    if (action) {
      where['action'] = { contains: action, mode: 'insensitive' };
    }

    if (from ?? to) {
      const createdAt: Record<string, Date> = {};
      if (from) createdAt['gte'] = from;
      if (to) createdAt['lte'] = to;
      where['createdAt'] = createdAt;
    }

    const [total, logs] = await Promise.all([
      this.prisma.client.auditLog.count({ where }),
      this.prisma.client.auditLog.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip: (page - 1) * pageSize,
        take: pageSize,
        include: { user: { select: { email: true } } },
      }),
    ]);

    const items: AuditLogEntry[] = logs.map((log) => ({
      id: log.id,
      userId: log.userId,
      userEmail: log.user?.email ?? null,
      action: log.action,
      resource: log.resource,
      metadata: log.metadata,
      ipAddress: log.ipAddress,
      requestId: log.requestId,
      createdAt: log.createdAt,
    }));

    return {
      items,
      total,
      page,
      pageSize,
      totalPages: Math.ceil(total / pageSize),
    };
  }
}
