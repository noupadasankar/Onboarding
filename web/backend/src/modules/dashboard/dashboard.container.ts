/**
 * Dashboard module DI bindings.
 */
import { ContainerModule } from 'inversify';
import { TYPES } from '../../core/di/types';
import { DashboardService, type IDashboardService } from './dashboard.service';
import { DashboardController } from './dashboard.controller';

export const dashboardModule = new ContainerModule((bind) => {
  bind<IDashboardService>(TYPES.DashboardService)
    .to(DashboardService)
    .inSingletonScope();

  bind<DashboardController>(TYPES.DashboardController)
    .to(DashboardController)
    .inSingletonScope();
});
