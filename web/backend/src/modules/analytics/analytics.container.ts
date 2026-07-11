/**
 * Analytics DI container binding.
 */
import { ContainerModule } from 'inversify';
import { TYPES } from '../../core/di/types';
import { AnalyticsService } from './analytics.service';
import { AnalyticsController } from './analytics.controller';
import type { IAnalyticsService } from './analytics.service';

export const analyticsModule = new ContainerModule((bind) => {
  bind<IAnalyticsService>(TYPES.AnalyticsService)
    .to(AnalyticsService)
    .inSingletonScope();

  bind<AnalyticsController>(TYPES.AnalyticsController)
    .to(AnalyticsController)
    .inSingletonScope();
});
