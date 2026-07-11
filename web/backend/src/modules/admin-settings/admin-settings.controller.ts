/**
 * Admin Settings HTTP controller.
 *
 * GET    /api/v1/admin/settings           — list all settings
 * GET    /api/v1/admin/settings/:key      — get one setting
 * PUT    /api/v1/admin/settings/:key      — upsert a setting
 * DELETE /api/v1/admin/settings/:key      — remove a setting
 */
import type { Request, Response } from 'express';
import { inject, injectable } from 'inversify';
import { TYPES } from '../../core/di/types';
import { asyncHandler } from '../../core/http/async-handler';
import { ApiResponse } from '../../core/http/api-response';
import type { IAdminSettingService } from './application/admin-setting.service';

@injectable()
export class AdminSettingsController {
  constructor(
    @inject(TYPES.AdminSettingService) private readonly svc: IAdminSettingService,
  ) {}

  listAll = asyncHandler(async (_req: Request, res: Response) => {
    ApiResponse.success(res, await this.svc.listAll());
  });

  getOne = asyncHandler(async (req: Request, res: Response) => {
    ApiResponse.success(res, await this.svc.get(req.params['key']!));
  });

  upsert = asyncHandler(async (req: Request, res: Response) => {
    const { value, description } = req.body as { value: unknown; description?: string };
    const result = await this.svc.set(
      req.params['key']!,
      value,
      req.auth!.id,
      description,
    );
    ApiResponse.success(res, result);
  });

  remove = asyncHandler(async (req: Request, res: Response) => {
    await this.svc.remove(req.params['key']!);
    ApiResponse.success(res, { deleted: true });
  });
}
