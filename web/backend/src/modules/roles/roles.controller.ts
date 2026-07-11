import { inject, injectable } from 'inversify';
import type { Request, Response } from 'express';
import { TYPES } from '../../core/di/types';
import { sendSuccess } from '../../core/http/api-response';
import type { IRoleCatalogService } from './role-catalog.service';

@injectable()
export class RolesController {
  constructor(
    @inject(TYPES.RoleCatalogService) private readonly catalog: IRoleCatalogService,
  ) {}

  getRoles = (_req: Request, res: Response): void => {
    sendSuccess(res, this.catalog.getRoles());
  };

  getPermissions = (_req: Request, res: Response): void => {
    sendSuccess(res, this.catalog.getPermissions());
  };
}
