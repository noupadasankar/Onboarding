/**
 * Notification domain types and repository interface.
 */

export interface NotificationDTO {
  id: string;
  userId: string;
  type: string;
  title: string;
  body: string;
  metadata: unknown;
  isRead: boolean;
  readAt: Date | null;
  createdAt: Date;
}

export interface CreateNotificationInput {
  userId: string;
  type: string;
  title: string;
  body: string;
  metadata?: Record<string, unknown>;
}

export interface INotificationRepository {
  findByUser(
    userId: string,
    opts: { page: number; pageSize: number; unreadOnly?: boolean },
  ): Promise<{ items: NotificationDTO[]; total: number }>;
  create(input: CreateNotificationInput): Promise<NotificationDTO>;
  markRead(id: string, userId: string): Promise<void>;
  markAllRead(userId: string): Promise<number>;
  countUnread(userId: string): Promise<number>;
}
