/**
 * Department HTTP controller — thin layer, delegates to DepartmentService.
 *
 * GET  /api/v1/departments           — list active departments
 * GET  /api/v1/departments/:id       — get one
 * POST /api/v1/departments           — create (admin only)
 * PATCH /api/v1/departments/:id      — update (admin only)
 */
import { Request, Response } from 'express';
import { inject, injectable } from 'inversify';
import { TYPES } from '../../core/di/types';
import { asyncHandler } from '../../core/http/async-handler';
import { ApiResponse } from '../../core/http/api-response';
import type { IDepartmentService } from './application/department.service';

@injectable()
export class DepartmentController {
  constructor(
    @inject(TYPES.DepartmentService) private readonly depts: IDepartmentService,
  ) {}

  list = asyncHandler(async (req: Request, res: Response) => {
    const includeInactive = req.query['includeInactive'] === 'true';
    const data = await this.depts.list(includeInactive);
    ApiResponse.success(res, data);
  });

  getById = asyncHandler(async (req: Request, res: Response) => {
    const data = await this.depts.getById(req.params['id']!);
    ApiResponse.success(res, data);
  });

  create = asyncHandler(async (req: Request, res: Response) => {
    const data = await this.depts.create(req.body);
    ApiResponse.created(res, data);
  });

  update = asyncHandler(async (req: Request, res: Response) => {
    const data = await this.depts.update(req.params['id']!, req.body);
    ApiResponse.success(res, data);
  });
}
