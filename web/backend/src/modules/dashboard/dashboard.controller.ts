/**
 * Dashboard HTTP controller. Exposes aggregated platform stats to authenticated
 * users. No business logic — delegates entirely to DashboardService.
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../core/di/types';
import { ApiResponse } from '../../core/http/api-response';
import { asyncHandler } from '../../core/http/async-handler';
import type { IDashboardService } from './dashboard.service';

@injectable()
export class DashboardController {
  constructor(
    @inject(TYPES.DashboardService) private readonly svc: IDashboardService,
  ) {}

  getStats = asyncHandler(async (req, res) => {
    const data = await this.svc.getStats(req.auth!.role);
    ApiResponse.success(res, data);
  });
}
