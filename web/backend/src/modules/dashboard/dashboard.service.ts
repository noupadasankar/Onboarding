/**
 * Dashboard service — aggregates platform-wide statistics for the dashboard view.
 * Runs all Prisma queries in parallel then stitches the result into DashboardStats.
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../core/di/types';
import type { PrismaService } from '../../infrastructure/database/prisma.service';
import type { Logger } from 'pino';
import type { IAiGateway } from '../../infrastructure/ai/ai-gateway';
import type { IDepartmentAccessService } from '../../core/auth/department-access.service';

/**
 * Enterprise document metrics for one department, scoped to the requesting
 * admin's role. `null` for roles that own no department (e.g. EMPLOYEE), which
 * per spec must NOT see document statistics.
 */
export interface DepartmentDocumentStats {
  department: string;
  indexed: number;
  pending: number; // PENDING + INDEXING
  failed: number;
  totalVectors: number;
  totalChunks: number;
  storageBytes: number;
  latestUploadAt: Date | null;
  latestIndexedAt: Date | null;
  avgIndexingSeconds: number | null;
}

export interface DashboardStats {
  users: { total: number; active: number };
  documents: { total: number; byStatus: Record<string, number> };
  conversations: { total: number; today: number };
  recentUploads: Array<{
    id: string;
    originalName: string;
    status: string;
    uploadedBy: string;
    createdAt: Date;
  }>;
  recentConversations: Array<{
    id: string;
    title: string | null;
    messageCount: number;
    createdAt: Date;
  }>;
  /** Department-scoped document metrics; null for employees (chat-only). */
  documentStats: DepartmentDocumentStats | null;
  health: { database: boolean; aiService: boolean };
}

export interface IDashboardService {
  /** @param role authenticated caller's role — scopes department document stats. */
  getStats(role: string): Promise<DashboardStats>;
}

@injectable()
export class DashboardService implements IDashboardService {
  constructor(
    @inject(TYPES.PrismaService) private readonly prisma: PrismaService,
    @inject(TYPES.Logger) private readonly logger: Logger,
    @inject(TYPES.AiGateway) private readonly ai: IAiGateway,
    @inject(TYPES.DepartmentAccessService)
    private readonly access: IDepartmentAccessService,
  ) {}

  async getStats(role: string): Promise<DashboardStats> {
    const startOfToday = new Date();
    startOfToday.setHours(0, 0, 0, 0);

    const [
      totalUsers,
      activeUsers,
      totalDocuments,
      documentsByStatus,
      totalConversations,
      todayConversations,
      recentDocuments,
      recentConvs,
    ] = await Promise.all([
      this.prisma.client.user.count(),
      this.prisma.client.user.count({ where: { isActive: true } }),
      this.prisma.client.document.count({ where: { status: { not: 'DELETED' } } }),
      this.prisma.client.document.groupBy({ by: ['status'], _count: true }),
      this.prisma.client.conversation.count(),
      this.prisma.client.conversation.count({
        where: { createdAt: { gte: startOfToday } },
      }),
      this.prisma.client.document.findMany({
        where: { status: { not: 'DELETED' } },
        orderBy: { createdAt: 'desc' },
        take: 5,
        include: { uploadedBy: { select: { email: true } } },
      }),
      this.prisma.client.conversation.findMany({
        orderBy: { createdAt: 'desc' },
        take: 5,
        include: { _count: { select: { messages: true } } },
      }),
    ]);

    let aiHealthy = false;
    try {
      const h = await this.ai.health();
      aiHealthy = h.status === 'ok';
    } catch (err) {
      this.logger.warn({ err }, 'dashboard:ai_health_check_failed');
      aiHealthy = false;
    }

    const byStatus = documentsByStatus.reduce<Record<string, number>>((acc, row) => {
      acc[row.status] = row._count;
      return acc;
    }, {});

    const recentUploads = recentDocuments.map((doc) => ({
      id: doc.id,
      originalName: doc.originalName,
      status: doc.status,
      uploadedBy: doc.uploadedBy.email,
      createdAt: doc.createdAt,
    }));

    const recentConversations = recentConvs.map((conv) => ({
      id: conv.id,
      title: conv.title,
      messageCount: conv._count.messages,
      createdAt: conv.createdAt,
    }));

    // Department-scoped document metrics — only for admins that own a department.
    const documentStats = await this._departmentDocumentStats(role);

    return {
      users: { total: totalUsers, active: activeUsers },
      documents: { total: totalDocuments, byStatus },
      conversations: { total: totalConversations, today: todayConversations },
      recentUploads,
      recentConversations,
      documentStats,
      health: { database: true, aiService: aiHealthy },
    };
  }

  /**
   * Compute enterprise document metrics for the caller's own department. Returns
   * null for roles that own no department (employees), which must not see
   * document statistics.
   */
  private async _departmentDocumentStats(
    role: string,
  ): Promise<DepartmentDocumentStats | null> {
    const deptName = this.access.getDepartmentForRole(role);
    if (!deptName) return null;

    const dept = await this.prisma.client.department.findUnique({
      where: { name: deptName },
      select: { id: true },
    });
    if (!dept) return null;

    // Only count the current (latest, non-deleted) documents for this department.
    const scope = { departmentId: dept.id, isLatest: true, status: { not: 'DELETED' as const } };

    const [byStatus, aggregates, indexedDocs] = await Promise.all([
      this.prisma.client.document.groupBy({
        by: ['status'],
        where: scope,
        _count: true,
      }),
      this.prisma.client.document.aggregate({
        where: scope,
        _sum: { vectorCount: true, chunkCount: true, sizeBytes: true },
        _max: { createdAt: true },
      }),
      // For latest-indexed time + average indexing duration.
      this.prisma.client.document.findMany({
        where: { ...scope, status: 'INDEXED' },
        select: { createdAt: true, updatedAt: true },
      }),
    ]);

    const counts = byStatus.reduce<Record<string, number>>((acc, row) => {
      acc[row.status] = row._count;
      return acc;
    }, {});

    // latestIndexedAt = most recent updatedAt among INDEXED docs; avg indexing
    // seconds derived from createdAt → updatedAt (upload → indexed) transitions.
    let latestIndexedAt: Date | null = null;
    let avgIndexingSeconds: number | null = null;
    if (indexedDocs.length > 0) {
      let totalSeconds = 0;
      for (const d of indexedDocs) {
        if (!latestIndexedAt || d.updatedAt > latestIndexedAt) latestIndexedAt = d.updatedAt;
        totalSeconds += Math.max(0, (d.updatedAt.getTime() - d.createdAt.getTime()) / 1000);
      }
      avgIndexingSeconds = Math.round((totalSeconds / indexedDocs.length) * 10) / 10;
    }

    return {
      department: deptName,
      indexed: counts['INDEXED'] ?? 0,
      pending: (counts['PENDING'] ?? 0) + (counts['INDEXING'] ?? 0),
      failed: counts['FAILED'] ?? 0,
      totalVectors: aggregates._sum.vectorCount ?? 0,
      totalChunks: aggregates._sum.chunkCount ?? 0,
      storageBytes: aggregates._sum.sizeBytes ?? 0,
      latestUploadAt: aggregates._max.createdAt ?? null,
      latestIndexedAt,
      avgIndexingSeconds,
    };
  }
}
