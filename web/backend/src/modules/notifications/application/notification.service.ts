/**
 * Notification application service.
 *
 * - Users read their own notifications and mark them read.
 * - Other services (DocumentService) call notify() to create notifications.
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../../core/di/types';
import type {
  CreateNotificationInput,
  INotificationRepository,
  NotificationDTO,
} from '../domain/notification.repository';

export interface INotificationService {
  list(
    userId: string,
    page: number,
    pageSize: number,
    unreadOnly?: boolean,
  ): Promise<{ items: NotificationDTO[]; total: number; unreadCount: number }>;
  markRead(id: string, userId: string): Promise<void>;
  markAllRead(userId: string): Promise<{ updated: number }>;
  notify(input: CreateNotificationInput): Promise<NotificationDTO>;
}

@injectable()
export class NotificationService implements INotificationService {
  constructor(
    @inject(TYPES.NotificationRepository) private readonly repo: INotificationRepository,
  ) {}

  async list(userId: string, page: number, pageSize: number, unreadOnly = false) {
    const [{ items, total }, unreadCount] = await Promise.all([
      this.repo.findByUser(userId, { page, pageSize, unreadOnly }),
      this.repo.countUnread(userId),
    ]);
    return { items, total, unreadCount };
  }

  async markRead(id: string, userId: string): Promise<void> {
    await this.repo.markRead(id, userId);
  }

  async markAllRead(userId: string): Promise<{ updated: number }> {
    const updated = await this.repo.markAllRead(userId);
    return { updated };
  }

  async notify(input: CreateNotificationInput): Promise<NotificationDTO> {
    return this.repo.create(input);
  }
}
