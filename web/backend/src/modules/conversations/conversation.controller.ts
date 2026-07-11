/**
 * Conversation HTTP controller.
 *
 * GET    /api/v1/conversations              — list user's conversations
 * GET    /api/v1/conversations/:id          — get with messages
 * POST   /api/v1/conversations/chat         — send message / start chat
 * DELETE /api/v1/conversations/:id          — archive
 */
import type { Request, Response } from 'express';
import { inject, injectable } from 'inversify';
import { TYPES } from '../../core/di/types';
import { asyncHandler } from '../../core/http/async-handler';
import { ApiResponse } from '../../core/http/api-response';
import type { IConversationService } from './application/conversation.service';

@injectable()
export class ConversationController {
  constructor(
    @inject(TYPES.ConversationService) private readonly svc: IConversationService,
  ) {}

  list = asyncHandler(async (req: Request, res: Response) => {
    const userId = req.auth!.id;
    const page = Math.max(1, Number(req.query['page'] ?? 1));
    const pageSize = Math.min(50, Math.max(1, Number(req.query['pageSize'] ?? 20)));
    const result = await this.svc.list(userId, page, pageSize);
    ApiResponse.success(res, result);
  });

  getById = asyncHandler(async (req: Request, res: Response) => {
    const data = await this.svc.getById(req.params['id']!, req.auth!.id);
    ApiResponse.success(res, data);
  });

  chat = asyncHandler(async (req: Request, res: Response) => {
    const user = req.auth!;
    const body = req.body as {
      question: string;
      conversationId?: string;
      departmentHint?: string;
      topK?: number;
      minScore?: number;
    };

    const result = await this.svc.chat({
      userId: user.id,
      userRole: user.role,
      userDepartment: null,
      conversationId: body.conversationId ?? null,
      question: body.question,
      departmentHint: body.departmentHint ?? null,
      topK: body.topK,
      minScore: body.minScore,
      requestId: res.locals.requestId,
    });

    ApiResponse.success(res, result);
  });

  archive = asyncHandler(async (req: Request, res: Response) => {
    await this.svc.archive(req.params['id']!, req.auth!.id);
    ApiResponse.success(res, { archived: true });
  });
}
