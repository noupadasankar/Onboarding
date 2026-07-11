/**
 * Analytics HTTP controller.
 *
 * GET /api/v1/analytics — returns aggregated platform analytics data.
 */
import { Request, Response } from 'express';
import { inject, injectable } from 'inversify';
import { TYPES } from '../../core/di/types';
import { asyncHandler } from '../../core/http/async-handler';
import { ApiResponse } from '../../core/http/api-response';
import type { IAnalyticsService } from './analytics.service';

@injectable()
export class AnalyticsController {
  constructor(
    @inject(TYPES.AnalyticsService) private readonly svc: IAnalyticsService,
  ) {}

  getData = asyncHandler(async (_req: Request, res: Response) => {
    ApiResponse.success(res, await this.svc.getData());
  });
}
