/**
 * Analytics application service.
 *
 * Aggregates platform-level metrics:
 *   - Questions asked per day (last 7 days)
 *   - Documents grouped by department
 *   - Token usage totals
 *   - Distinct active users in the last 7 days
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../core/di/types';
import type { PrismaService } from '../../infrastructure/database/prisma.service';
import type { Logger } from '../../core/logging/logger';

export type AnalyticsData = {
  questionsPerDay: Array<{ date: string; count: number }>;
  documentsByDepartment: Array<{ department: string; count: number }>;
  tokenUsage: { totalPrompt: number; totalCompletion: number; totalMessages: number };
  activeUsersLast7Days: number;
};

export interface IAnalyticsService {
  getData(): Promise<AnalyticsData>;
}

@injectable()
export class AnalyticsService implements IAnalyticsService {
  constructor(
    @inject(TYPES.PrismaService) private readonly prisma: PrismaService,
    @inject(TYPES.Logger) private readonly logger: Logger,
  ) {}

  async getData(): Promise<AnalyticsData> {
    this.logger.info('Analytics: building analytics data');

    const [questionsPerDay, documentsByDepartment, tokenUsage, activeUsersLast7Days] =
      await Promise.all([
        this._questionsPerDay(),
        this._documentsByDepartment(),
        this._tokenUsage(),
        this._activeUsersLast7Days(),
      ]);

    return { questionsPerDay, documentsByDepartment, tokenUsage, activeUsersLast7Days };
  }

  // ── helpers ────────────────────────────────────────────────────────────────

  private async _questionsPerDay(): Promise<Array<{ date: string; count: number }>> {
    const dates = Array.from({ length: 7 }, (_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - (6 - i));
      d.setHours(0, 0, 0, 0);
      return d;
    });

    const counts = await Promise.all(
      dates.map((d) => {
        const nextDay = new Date(d);
        nextDay.setDate(nextDay.getDate() + 1);

        return this.prisma.client.message.count({
          where: {
            role: 'user',
            createdAt: { gte: d, lt: nextDay },
          },
        });
      }),
    );

    return dates.map((d, i) => ({
      date: d.toISOString().slice(0, 10),
      count: counts[i]!,
    }));
  }

  private async _documentsByDepartment(): Promise<
    Array<{ department: string; count: number }>
  > {
    const groups = await this.prisma.client.document.groupBy({
      by: ['departmentId'],
      _count: true,
      where: { status: { not: 'DELETED' } },
    });

    const withNames = await Promise.all(
      groups.map(async (g) => {
        const dept = await this.prisma.client.department.findUnique({
          where: { id: g.departmentId },
        });
        return {
          department: dept?.name ?? 'unassigned',
          count: g._count,
        };
      }),
    );

    return withNames.sort((a, b) => b.count - a.count);
  }

  private async _tokenUsage(): Promise<{
    totalPrompt: number;
    totalCompletion: number;
    totalMessages: number;
  }> {
    const result = await this.prisma.client.message.aggregate({
      _sum: { promptTokens: true, completionTokens: true },
      _count: { id: true },
    });

    return {
      totalPrompt: result._sum.promptTokens ?? 0,
      totalCompletion: result._sum.completionTokens ?? 0,
      totalMessages: result._count.id,
    };
  }

  private async _activeUsersLast7Days(): Promise<number> {
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

    const groups = await this.prisma.client.conversation.groupBy({
      by: ['userId'],
      where: { createdAt: { gte: sevenDaysAgo } },
    });

    return groups.length;
  }
}
