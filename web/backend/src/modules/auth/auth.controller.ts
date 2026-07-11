/**
 * Auth HTTP controller. HTTP ↔ service translation only. Reads validated bodies,
 * calls the service, writes the shared envelope.
 */
import { inject, injectable } from 'inversify';
import type { Request, Response } from 'express';
import type { LoginInput, RefreshInput } from '@optiagent/shared';
import { TYPES } from '../../core/di/types';
import { sendSuccess } from '../../core/http/api-response';
import type { IAuthService } from './application/auth.service';

@injectable()
export class AuthController {
  constructor(@inject(TYPES.AuthService) private readonly auth: IAuthService) {}

  login = async (req: Request, res: Response): Promise<void> => {
    const { email, password } = req.body as LoginInput;
    const result = await this.auth.login(email, password, {
      ipAddress: req.ip,
      requestId: res.locals.requestId,
    });
    sendSuccess(res, result);
  };

  refresh = async (req: Request, res: Response): Promise<void> => {
    const { refreshToken } = req.body as RefreshInput;
    const result = await this.auth.refresh(refreshToken);
    sendSuccess(res, result);
  };

  logout = async (req: Request, res: Response): Promise<void> => {
    const { refreshToken } = req.body as RefreshInput;
    await this.auth.logout(refreshToken, {
      ipAddress: req.ip,
      requestId: res.locals.requestId,
    });
    sendSuccess(res, { loggedOut: true });
  };

  me = async (req: Request, res: Response): Promise<void> => {
    sendSuccess(res, req.auth);
  };
}
