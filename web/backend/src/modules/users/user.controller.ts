/**
 * Users HTTP controller. Translates HTTP ↔ service calls only — no business logic,
 * no DB access. Resolved from the DI container by the route module.
 */
import { inject, injectable } from 'inversify';
import type { Request, Response } from 'express';
import type { CreateUserRequest, UpdateUserRequest, UserListQuery } from '@optiagent/shared';
import { TYPES } from '../../core/di/types';
import { sendSuccess } from '../../core/http/api-response';
import type { IUserService } from './application/user.service';

@injectable()
export class UserController {
  constructor(@inject(TYPES.UserService) private readonly users: IUserService) {}

  list = async (req: Request, res: Response): Promise<void> => {
    const { page, pageSize, search, role, isActive } = req.query as unknown as UserListQuery;
    const result = await this.users.list(page, pageSize, { search, role, isActive });
    sendSuccess(res, result);
  };

  me = async (req: Request, res: Response): Promise<void> => {
    const user = await this.users.me(req.auth!.id);
    sendSuccess(res, user);
  };

  getById = async (req: Request, res: Response): Promise<void> => {
    const user = await this.users.getById(req.params['id']!);
    sendSuccess(res, user);
  };

  create = async (req: Request, res: Response): Promise<void> => {
    const user = await this.users.create(req.body as CreateUserRequest, {
      actorId: req.auth?.id,
      ipAddress: req.ip,
      requestId: res.locals.requestId,
    });
    res.status(201);
    sendSuccess(res, user);
  };

  update = async (req: Request, res: Response): Promise<void> => {
    const user = await this.users.update(req.params['id']!, req.body as UpdateUserRequest, {
      actorId: req.auth?.id,
      ipAddress: req.ip,
      requestId: res.locals.requestId,
    });
    sendSuccess(res, user);
  };

  deactivate = async (req: Request, res: Response): Promise<void> => {
    await this.users.deactivate(req.params['id']!, {
      actorId: req.auth?.id,
      ipAddress: req.ip,
      requestId: res.locals.requestId,
    });
    sendSuccess(res, { deactivated: true });
  };
}
