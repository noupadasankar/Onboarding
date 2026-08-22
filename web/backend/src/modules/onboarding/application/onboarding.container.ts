/** Onboarding module DI container. */
import { ContainerModule } from 'inversify';
import { TYPES } from '../../../core/di/types';
import type { OnboardingTaskRepository } from '../domain/onboarding-task.entity';
import { InMemoryOnboardingTaskRepository } from '../infrastructure/onboarding-task.memory.repository';
import { OnboardingTaskService } from './onboarding-task.service';
import { OnboardingTaskController } from './onboarding-task.controller';

export const onboardingModule = new ContainerModule((bind) => {
  bind<OnboardingTaskRepository>(TYPES.OnboardingTaskRepository)
    .to(InMemoryOnboardingTaskRepository)
    .inSingletonScope();

  bind<OnboardingTaskService>(TYPES.OnboardingTaskService)
    .to(OnboardingTaskService)
    .inSingletonScope();

  bind<OnboardingTaskController>(TYPES.OnboardingTaskController)
    .to(OnboardingTaskController)
    .inSingletonScope();
});

