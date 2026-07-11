/**
 * Department DI container binding.
 */
import { ContainerModule } from 'inversify';
import { TYPES } from '../../core/di/types';
import { DepartmentPrismaRepository } from './infrastructure/department.prisma.repository';
import { DepartmentService } from './application/department.service';
import { DepartmentController } from './department.controller';
import type { IDepartmentRepository } from './domain/department.repository';
import type { IDepartmentService } from './application/department.service';

export const departmentModule = new ContainerModule((bind) => {
  bind<IDepartmentRepository>(TYPES.DepartmentRepository)
    .to(DepartmentPrismaRepository)
    .inSingletonScope();

  bind<IDepartmentService>(TYPES.DepartmentService)
    .to(DepartmentService)
    .inSingletonScope();

  bind<DepartmentController>(TYPES.DepartmentController)
    .to(DepartmentController)
    .inSingletonScope();
});
