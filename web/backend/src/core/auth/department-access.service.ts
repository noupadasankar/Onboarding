/**
 * DepartmentAccessService — the single authority for "which department(s) may
 * this role touch, and how". All role → department policy lives here so that
 * introducing a future role (e.g. LEGAL_MANAGER, SALES_MANAGER) is a one-file
 * change: extend the shared `departmentForRole` map and, if needed, the guards
 * below. Call sites ask *questions* ("can this role upload?", "which department
 * does it own?") and never branch on role literals themselves.
 *
 * Pure policy — no I/O, no DB. Department name → UUID resolution is a separate
 * concern handled by the repository layer.
 */
import { injectable } from 'inversify';
import {
  Role,
  Permission,
  allowedDepartmentsForRole,
  departmentForRole,
  roleHasPermission,
  type DepartmentName,
} from '@hr-onboarding/shared';

export interface IDepartmentAccessService {
  /** The canonical department a role uploads to / administers, or null. */
  getDepartmentForRole(role: string): DepartmentName | null;
  /** Departments a role may read from (chat/search). Never empty for readers. */
  allowedDepartments(role: string): DepartmentName[];
  /** True when `departmentName` is within the role's readable/manageable scope. */
  canAccessDepartment(role: string, departmentName: string | null): boolean;
  /** True when the role may upload documents at all. */
  canUpload(role: string): boolean;
  /** True when the role may download document files. */
  canDownload(role: string): boolean;
}

@injectable()
export class DepartmentAccessService implements IDepartmentAccessService {
  getDepartmentForRole(role: string): DepartmentName | null {
    return departmentForRole(role as Role);
  }

  allowedDepartments(role: string): DepartmentName[] {
    return allowedDepartmentsForRole(role as Role);
  }

  canAccessDepartment(role: string, departmentName: string | null): boolean {
    if (!departmentName) return false;
    return this.allowedDepartments(role).includes(departmentName as DepartmentName);
  }

  canUpload(role: string): boolean {
    // Must both hold the permission and own a department to upload into.
    return (
      roleHasPermission(role as Role, Permission.DOCUMENTS_UPLOAD) &&
      this.getDepartmentForRole(role) !== null
    );
  }

  canDownload(role: string): boolean {
    return roleHasPermission(role as Role, Permission.DOCUMENTS_VIEW);
  }
}
