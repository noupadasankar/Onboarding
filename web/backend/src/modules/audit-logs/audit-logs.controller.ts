/**
 * Audit log HTTP controller. Exposes a single list endpoint that returns a
 * paginated, filtered view of audit log entries. Read-only — no mutations.
 */
import { inject, injectable } from 'inversify';
import type { Request, Response } from 'express';
import { TYPES } from '../../core/di/types';
import { ApiResponse } from '../../core/http/api-response';
import { asyncHandler } from '../../core/http/async-handler';
import type { IAuditLogViewService } from './audit-logs.service';

@injectable()
export class AuditLogViewController {
  constructor(
    @inject(TYPES.AuditLogViewService) private readonly svc: IAuditLogViewService,
  ) {}

  list = asyncHandler(async (req: Request, res: Response) => {
    const page = Math.max(1, Number(req.query['page'] ?? 1));
    const pageSize = Math.min(100, Math.max(1, Number(req.query['pageSize'] ?? 20)));

    const opts = {
      page,
      pageSize,
      userId: req.query['userId'] as string | undefined,
      action: req.query['action'] as string | undefined,
      from: req.query['from'] ? new Date(req.query['from'] as string) : undefined,
      to: req.query['to'] ? new Date(req.query['to'] as string) : undefined,
    };

    ApiResponse.success(res, await this.svc.list(opts));
  });
}
