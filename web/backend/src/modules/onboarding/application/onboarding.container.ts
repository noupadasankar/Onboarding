/** Onboarding module DI container. */
import { Container, type Binding } from 'inversify';
import { TYPES } from '../../../core/di/types';
import type { OnboardingTaskRepository } from '../domain/onboarding-task.entity';
import { InMemoryOnboardingTaskRepository } from '../infrastructure/onboarding-task.memory.repository';
import { OnboardingTaskService } from '../application/onboarding-task.service';
import { OnboardingTaskController } from '../application/onboarding-task.controller';
import { createOnboardingRoutes } from '../application/onboarding-task.routes';

export const onboardingBindings: Binding[] = [
  {
    type: TYPES.OnboardingTaskRepository,
    to: InMemoryOnboardingTaskRepository,
    inSingletonScope: true,
  },
  {
    type: TYPES.OnboardingTaskService,
    to: OnboardingTaskService,
    inSingletonScope: true,
  },
  {
    type: TYPES.OnboardingTaskController,
    to: OnboardingTaskController,
    inSingletonScope: true,
  },
  {
    type: TYPES.OnboardingRoutesFactory,
    toConstantValue: createOnboardingRoutes,
  },
];

export function registerOnboardingBindings(container: Container): void {
  onboardingBindings.forEach((b) => {
    if ('toConstantValue' in b) {
      container.bind(b.type).toConstantValue(b.toConstantValue);
    } else if (b.inSingletonScope) {
      container.bind(b.type).to(b.to).inSingletonScope();
    } else {
      container.bind(b.type).to(b.to);
    }
  });
}
