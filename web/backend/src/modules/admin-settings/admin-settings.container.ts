/**
 * Admin Settings DI container bindings.
 */
import { ContainerModule } from 'inversify';
import { TYPES } from '../../core/di/types';
import { AdminSettingPrismaRepository } from './infrastructure/admin-setting.prisma.repository';
import { AdminSettingService } from './application/admin-setting.service';
import { AdminSettingsController } from './admin-settings.controller';
import type { IAdminSettingRepository } from './domain/admin-setting.repository';
import type { IAdminSettingService } from './application/admin-setting.service';

export const adminSettingsModule = new ContainerModule((bind) => {
  bind<IAdminSettingRepository>(TYPES.AdminSettingRepository)
    .to(AdminSettingPrismaRepository)
    .inSingletonScope();

  bind<IAdminSettingService>(TYPES.AdminSettingService)
    .to(AdminSettingService)
    .inSingletonScope();

  bind<AdminSettingsController>(TYPES.AdminSettingsController)
    .to(AdminSettingsController)
    .inSingletonScope();
});
