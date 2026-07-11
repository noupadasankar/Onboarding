import { injectable } from 'inversify';
import { ALL_PERMISSIONS, ALL_ROLES, permissionsForRole } from '@optiagent/shared';
import type { Permission, RoleDTO } from '@optiagent/shared';

export interface IRoleCatalogService {
  getRoles(): RoleDTO[];
  getPermissions(): Permission[];
}

@injectable()
export class RoleCatalogService implements IRoleCatalogService {
  getRoles(): RoleDTO[] {
    return ALL_ROLES.map((name) => ({ name, permissions: [...permissionsForRole(name)] }));
  }

  getPermissions(): Permission[] {
    return [...ALL_PERMISSIONS];
  }
}
