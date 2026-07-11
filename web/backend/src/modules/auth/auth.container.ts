/**
 * Auth module DI bindings.
 */
import type { Container } from 'inversify';
import { TYPES } from '../../core/di/types';
import { AuthService, type IAuthService } from './application/auth.service';
import { AuthController } from './auth.controller';

export function bindAuthModule(container: Container): void {
  container.bind<IAuthService>(TYPES.AuthService).to(AuthService).inSingletonScope();
  container.bind<AuthController>(TYPES.AuthController).to(AuthController).inSingletonScope();
}
