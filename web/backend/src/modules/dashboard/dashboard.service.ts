/**
 * Dashboard service — aggregates platform-wide statistics for the dashboard view.
 * Runs all Prisma queries in parallel then stitches the result into DashboardStats.
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../core/di/types';
import type { PrismaService } from '../../infrastructure/database/prisma.service';
import type { Logger } from 'pino';
import type { IAiGateway } from '../../infrastructure/ai/ai-gateway';

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
  health: { database: boolean; aiService: boolean };
}

export interface IDashboardService {
  getStats(): Promise<DashboardStats>;
}

@injectable()
export class DashboardService implements IDashboardService {
  constructor(
    @inject(TYPES.PrismaService) private readonly prisma: PrismaService,
    @inject(TYPES.Logger) private readonly logger: Logger,
    @inject(TYPES.AiGateway) private readonly ai: IAiGateway,
  ) {}

  async getStats(): Promise<DashboardStats> {
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

    return {
      users: { total: totalUsers, active: activeUsers },
      documents: { total: totalDocuments, byStatus },
      conversations: { total: totalConversations, today: todayConversations },
      recentUploads,
      recentConversations,
      health: { database: true, aiService: aiHealthy },
    };
  }
}
