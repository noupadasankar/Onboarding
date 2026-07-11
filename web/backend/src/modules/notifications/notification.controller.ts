/**
 * Notification HTTP controller.
 *
 * GET    /api/v1/notifications            — list (paginated)
 * PATCH  /api/v1/notifications/:id/read   — mark one as read
 * PATCH  /api/v1/notifications/read-all   — mark all as read
 */
import type { Request, Response } from 'express';
import { inject, injectable } from 'inversify';
import { TYPES } from '../../core/di/types';
import { asyncHandler } from '../../core/http/async-handler';
import { ApiResponse } from '../../core/http/api-response';
import type { INotificationService } from './application/notification.service';

@injectable()
export class NotificationController {
  constructor(
    @inject(TYPES.NotificationService) private readonly svc: INotificationService,
  ) {}

  list = asyncHandler(async (req: Request, res: Response) => {
    const userId = req.auth!.id;
    const page = Math.max(1, Number(req.query['page'] ?? 1));
    const pageSize = Math.min(50, Math.max(1, Number(req.query['pageSize'] ?? 20)));
    const unreadOnly = req.query['unreadOnly'] === 'true';
    const result = await this.svc.list(userId, page, pageSize, unreadOnly);
    ApiResponse.success(res, result);
  });

  markRead = asyncHandler(async (req: Request, res: Response) => {
    await this.svc.markRead(req.params['id']!, req.auth!.id);
    ApiResponse.success(res, { read: true });
  });

  markAllRead = asyncHandler(async (req: Request, res: Response) => {
    const result = await this.svc.markAllRead(req.auth!.id);
    ApiResponse.success(res, result);
  });
}
