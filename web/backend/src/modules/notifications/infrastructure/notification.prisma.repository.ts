/**
 * Prisma implementation of INotificationRepository.
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../../core/di/types';
import type { Prisma } from '@prisma/client';
import type { PrismaService } from '../../../infrastructure/database/prisma.service';
import type {
  CreateNotificationInput,
  INotificationRepository,
  NotificationDTO,
} from '../domain/notification.repository';

function toDTO(n: {
  id: string;
  userId: string;
  type: string;
  title: string;
  body: string;
  metadata: unknown;
  isRead: boolean;
  readAt: Date | null;
  createdAt: Date;
}): NotificationDTO {
  return {
    id: n.id,
    userId: n.userId,
    type: n.type,
    title: n.title,
    body: n.body,
    metadata: n.metadata,
    isRead: n.isRead,
    readAt: n.readAt,
    createdAt: n.createdAt,
  };
}

@injectable()
export class NotificationPrismaRepository implements INotificationRepository {
  constructor(@inject(TYPES.PrismaService) private readonly prisma: PrismaService) {}

  async findByUser(
    userId: string,
    opts: { page: number; pageSize: number; unreadOnly?: boolean },
  ): Promise<{ items: NotificationDTO[]; total: number }> {
    const where = { userId, ...(opts.unreadOnly ? { isRead: false } : {}) };
    const skip = (opts.page - 1) * opts.pageSize;

    const [total, rows] = await Promise.all([
      this.prisma.client.notification.count({ where }),
      this.prisma.client.notification.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip,
        take: opts.pageSize,
      }),
    ]);

    return { items: rows.map(toDTO), total };
  }

  async create(input: CreateNotificationInput): Promise<NotificationDTO> {
    const n = await this.prisma.client.notification.create({
      data: {
        userId: input.userId,
        type: input.type,
        title: input.title,
        body: input.body,
        metadata: (input.metadata ?? undefined) as Prisma.InputJsonValue | undefined,
      },
    });
    return toDTO(n);
  }

  async markRead(id: string, userId: string): Promise<void> {
    await this.prisma.client.notification.updateMany({
      where: { id, userId },
      data: { isRead: true, readAt: new Date() },
    });
  }

  async markAllRead(userId: string): Promise<number> {
    const result = await this.prisma.client.notification.updateMany({
      where: { userId, isRead: false },
      data: { isRead: true, readAt: new Date() },
    });
    return result.count;
  }

  async countUnread(userId: string): Promise<number> {
    return this.prisma.client.notification.count({ where: { userId, isRead: false } });
  }
}
