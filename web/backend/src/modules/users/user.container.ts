/**
 * Users module DI bindings. Each module owns its container wiring so the
 * composition root stays small and modules are self-describing.
 */
import type { Container } from 'inversify';
import { TYPES } from '../../core/di/types';
import type { IUserRepository } from './domain/user.repository';
import { UserPrismaRepository } from './infrastructure/user.prisma.repository';
import { UserService, type IUserService } from './application/user.service';
import { UserController } from './user.controller';

export function bindUsersModule(container: Container): void {
  container.bind<IUserRepository>(TYPES.UserRepository).to(UserPrismaRepository).inSingletonScope();
  container.bind<IUserService>(TYPES.UserService).to(UserService).inSingletonScope();
  container.bind<UserController>(TYPES.UserController).to(UserController).inSingletonScope();
}
