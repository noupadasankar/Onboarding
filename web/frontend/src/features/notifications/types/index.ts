export interface NotificationDTO {
  id: string;
  userId: string;
  type: string;
  title: string;
  body: string;
  metadata: unknown;
  isRead: boolean;
  readAt: string | null;
  createdAt: string;
}

export interface NotificationListResult {
  items: NotificationDTO[];
  total: number;
  unreadCount: number;
}
