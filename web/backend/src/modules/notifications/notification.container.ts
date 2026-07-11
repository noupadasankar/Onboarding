/**
 * Notification DI container bindings.
 */
import { ContainerModule } from 'inversify';
import { TYPES } from '../../core/di/types';
import { NotificationPrismaRepository } from './infrastructure/notification.prisma.repository';
import { NotificationService } from './application/notification.service';
import { NotificationController } from './notification.controller';
import type { INotificationRepository } from './domain/notification.repository';
import type { INotificationService } from './application/notification.service';

export const notificationModule = new ContainerModule((bind) => {
  bind<INotificationRepository>(TYPES.NotificationRepository)
    .to(NotificationPrismaRepository)
    .inSingletonScope();

  bind<INotificationService>(TYPES.NotificationService)
    .to(NotificationService)
    .inSingletonScope();

  bind<NotificationController>(TYPES.NotificationController)
    .to(NotificationController)
    .inSingletonScope();
});
