/**
 * Seeds roles, permissions (from the shared RBAC contract), and one demo user per
 * role. Idempotent — safe to run repeatedly. Run via `pnpm prisma:seed`.
 */
import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';
import {
  ALL_PERMISSIONS,
  ALL_ROLES,
  permissionsForRole,
  Role,
} from '@optiagent/shared';

const prisma = new PrismaClient();

const DEMO_PASSWORD = 'Password123!';
const BCRYPT_ROUNDS = 12;

/** One representative demo account per role. */
const DEMO_USERS: Array<{ email: string; role: Role; department: string }> = [
  { email: 'employee@optiagent.dev', role: Role.EMPLOYEE, department: 'Engineering' },
  { email: 'hr.manager@optiagent.dev', role: Role.HR_MANAGER, department: 'Human Resources' },
  { email: 'finance.admin@optiagent.dev', role: Role.FINANCE_ADMIN, department: 'Finance' },
  { email: 'it.admin@optiagent.dev', role: Role.IT_ADMIN, department: 'IT Operations' },
];

async function seedPermissions(): Promise<Map<string, string>> {
  const byKey = new Map<string, string>();
  for (const key of ALL_PERMISSIONS) {
    const perm = await prisma.permission.upsert({
      where: { key },
      update: {},
      create: { key },
    });
    byKey.set(key, perm.id);
  }
  return byKey;
}

async function seedRoles(permissionIds: Map<string, string>): Promise<Map<Role, string>> {
  const byRole = new Map<Role, string>();
  for (const roleName of ALL_ROLES) {
    const role = await prisma.role.upsert({
      where: { name: roleName },
      update: {},
      create: { name: roleName, description: `${roleName} role` },
    });
    byRole.set(roleName, role.id);

    // Reconcile grants to exactly match the shared contract.
    await prisma.rolePermission.deleteMany({ where: { roleId: role.id } });
    const grants = permissionsForRole(roleName)
      .map((key) => permissionIds.get(key))
      .filter((id): id is string => Boolean(id))
      .map((permissionId) => ({ roleId: role.id, permissionId }));
    if (grants.length > 0) {
      await prisma.rolePermission.createMany({ data: grants, skipDuplicates: true });
    }
  }
  return byRole;
}

async function seedUsers(roleIds: Map<Role, string>): Promise<void> {
  const passwordHash = await bcrypt.hash(DEMO_PASSWORD, BCRYPT_ROUNDS);
  for (const demo of DEMO_USERS) {
    const roleId = roleIds.get(demo.role);
    if (!roleId) continue;
    await prisma.user.upsert({
      where: { email: demo.email },
      update: { roleId, department: demo.department, isActive: true },
      create: {
        email: demo.email,
        passwordHash,
        department: demo.department,
        roleId,
      },
    });
  }
}

async function main(): Promise<void> {
  const permissionIds = await seedPermissions();
  const roleIds = await seedRoles(permissionIds);
  await seedUsers(roleIds);
  await seedDepartments();

  // eslint-disable-next-line no-console
  console.log('Seed complete. Demo users (password: %s):', DEMO_PASSWORD);
  for (const u of DEMO_USERS) {
    // eslint-disable-next-line no-console
    console.log(`  - ${u.email}  [${u.role}]`);
  }
}

async function seedDepartments(): Promise<void> {
  const departments = [
    { name: 'hr', displayName: 'Human Resources', description: 'HR policies, leave, benefits' },
    { name: 'finance', displayName: 'Finance', description: 'Expense policy, payroll, budgets' },
    { name: 'it', displayName: 'Information Technology', description: 'IT support, devices, access' },
    { name: 'general', displayName: 'General', description: 'Company-wide documents' },
  ];
  for (const dept of departments) {
    await prisma.department.upsert({
      where: { name: dept.name },
      update: { displayName: dept.displayName, description: dept.description },
      create: dept,
    });
  }
  // eslint-disable-next-line no-console
  console.log('Departments seeded: hr, finance, it, general');
}

main()
  .catch((err) => {
    // eslint-disable-next-line no-console
    console.error(err);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
