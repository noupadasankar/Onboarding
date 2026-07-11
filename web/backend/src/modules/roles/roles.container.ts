import type { Container } from 'inversify';
import { TYPES } from '../../core/di/types';
import { RoleCatalogService } from './role-catalog.service';
import type { IRoleCatalogService } from './role-catalog.service';
import { RolesController } from './roles.controller';

export function bindRolesModule(container: Container): void {
  container
    .bind<IRoleCatalogService>(TYPES.RoleCatalogService)
    .to(RoleCatalogService)
    .inSingletonScope();
  container.bind<RolesController>(TYPES.RolesController).to(RolesController).inSingletonScope();
}
