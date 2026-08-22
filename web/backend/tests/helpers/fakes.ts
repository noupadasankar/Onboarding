/**
 * In-memory fakes for integration tests — exercise the real HTTP pipeline,
 * middleware, DI wiring and security services without Postgres/Redis running.
 */
import { generateKeyPairSync } from 'node:crypto';
import pino from 'pino';
import { Container } from 'inversify';
import { Role } from '@hr-onboarding/shared';
import type { Paginated } from '@hr-onboarding/shared';
import { TYPES } from '../../src/core/di/types';
import type { AppConfig } from '../../src/config/env';
import { JwtService, type IJwtService } from '../../src/infrastructure/security/jwt.service';
import { BcryptPasswordService } from '../../src/infrastructure/security/password.service';
import type { IPasswordService } from '../../src/infrastructure/security/password.service';
import type { ITokenStore } from '../../src/infrastructure/security/token-store';
import { UserEntity } from '../../src/modules/users/domain/user.entity';
import type {
  CreateUserData,
  IUserRepository,
  UpdateUserData,
  UserListFilters,
} from '../../src/modules/users/domain/user.repository';
import type { IAuditLogService } from '../../src/infrastructure/audit/audit-log.service';
import { bindAuthModule } from '../../src/modules/auth/auth.container';
import { bindUsersModule } from '../../src/modules/users/user.container';
import { bindRolesModule } from '../../src/modules/roles/roles.container';
import { departmentModule } from '../../src/modules/departments/department.container';
import { documentModule } from '../../src/modules/documents/document.container';
import { conversationModule } from '../../src/modules/conversations/conversation.container';
import { dashboardModule } from '../../src/modules/dashboard/dashboard.container';
import { analyticsModule } from '../../src/modules/analytics/analytics.container';
import { auditLogsModule } from '../../src/modules/audit-logs/audit-logs.container';
import { notificationModule } from '../../src/modules/notifications/notification.container';
import { adminSettingsModule } from '../../src/modules/admin-settings/admin-settings.container';
import { onboardingModule } from '../../src/modules/onboarding/application/onboarding.container';
import { DepartmentAccessService } from '../../src/core/auth/department-access.service';
import { LocalStorageService } from '../../src/infrastructure/storage/local-storage.service';
import { BullMQIndexingQueue } from '../../src/infrastructure/queue/bullmq-indexing-queue';
import { AiGateway } from '../../src/infrastructure/ai/ai-gateway';

/** Build a valid AppConfig with a freshly generated RS256 keypair. */
export function makeTestConfig(): AppConfig {
  const { privateKey, publicKey } = generateKeyPairSync('rsa', {
    modulusLength: 2048,
    publicKeyEncoding: { type: 'spki', format: 'pem' },
    privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
  });
  return {
    nodeEnv: 'test',
    isProduction: false,
    port: 0,
    logLevel: 'silent',
    databaseUrl: 'postgresql://test',
    redisUrl: 'redis://test',
    jwt: {
      privateKey,
      publicKey,
      accessTtlSeconds: 900,
      refreshTtlSeconds: 604800,
      issuer: 'optiagent',
      audience: 'optiagent-clients',
    },
    corsOrigins: ['http://localhost:3000'],
    loginRateLimit: { max: 5, windowSeconds: 900 },
    aiService: { url: 'http://localhost:8100', internalToken: 'test' },
  };
}

/** Minimal in-memory stand-in for the ioredis client used by our code paths. */
class FakeRedisClient {
  private store = new Map<string, string>();
  async set(key: string, value: string): Promise<'OK'> {
    this.store.set(key, value);
    return 'OK';
  }
  async get(key: string): Promise<string | null> {
    return this.store.get(key) ?? null;
  }
  async exists(key: string): Promise<number> {
    return this.store.has(key) ? 1 : 0;
  }
  async del(key: string): Promise<number> {
    return this.store.delete(key) ? 1 : 0;
  }
  async incr(key: string): Promise<number> {
    const next = Number(this.store.get(key) ?? '0') + 1;
    this.store.set(key, String(next));
    return next;
  }
  async expire(): Promise<number> {
    return 1;
  }
  async ttl(): Promise<number> {
    return 900;
  }
  async ping(): Promise<'PONG'> {
    return 'PONG';
  }
}

export class FakeRedisService {
  readonly client = new FakeRedisClient() as unknown as import('ioredis').Redis;
  async connect(): Promise<void> {}
  async disconnect(): Promise<void> {}
  async healthCheck(): Promise<boolean> {
    return true;
  }
}

export class FakePrismaService {
  async connect(): Promise<void> {}
  async disconnect(): Promise<void> {}
  async healthCheck(): Promise<boolean> {
    return true;
  }
}

/** In-memory token store (mirrors RedisTokenStore semantics). */
export class InMemoryTokenStore implements ITokenStore {
  private active = new Set<string>();
  async store(jti: string): Promise<void> {
    this.active.add(jti);
  }
  async isActive(jti: string): Promise<boolean> {
    return this.active.has(jti);
  }
  async revoke(jti: string): Promise<void> {
    this.active.delete(jti);
  }
}

/** No-op audit service for tests — prevents audit writes from touching Postgres. */
export class FakeAuditLogService implements IAuditLogService {
  readonly entries: Array<{ action: string }> = [];
  async log(entry: { action: string }): Promise<void> {
    this.entries.push(entry);
  }
}

/** In-memory user repository seeded via `add`. */
export class InMemoryUserRepository implements IUserRepository {
  private byId = new Map<string, UserEntity>();

  add(user: UserEntity): void {
    this.byId.set(user.id, user);
  }
  async findByEmail(email: string): Promise<UserEntity | null> {
    return Array.from(this.byId.values()).find((u) => u.email === email) ?? null;
  }
  async findById(id: string): Promise<UserEntity | null> {
    return this.byId.get(id) ?? null;
  }
  async create(data: CreateUserData): Promise<UserEntity> {
    const user = new UserEntity({
      id: `u_${this.byId.size + 1}`,
      email: data.email,
      passwordHash: data.passwordHash,
      department: data.department ?? null,
      isActive: true,
      role: data.role,
      createdAt: new Date(),
    });
    this.add(user);
    return user;
  }
  async update(id: string, data: UpdateUserData): Promise<UserEntity | null> {
    const existing = this.byId.get(id);
    if (!existing) return null;
    const updated = new UserEntity({
      id: existing.id,
      email: existing.email,
      passwordHash: existing.passwordHash,
      department: data.department !== undefined ? data.department : existing.department,
      isActive: data.isActive !== undefined ? data.isActive : existing.isActive,
      role: data.role !== undefined ? data.role : existing.role,
      createdAt: existing.props.createdAt,
    });
    this.byId.set(id, updated);
    return updated;
  }
  async list(
    page: number,
    pageSize: number,
    filters?: UserListFilters,
  ): Promise<Paginated<UserEntity>> {
    let items = Array.from(this.byId.values());
    if (filters?.role !== undefined) items = items.filter((u) => u.role === filters.role);
    if (filters?.isActive !== undefined) items = items.filter((u) => u.isActive === filters.isActive);
    if (filters?.search) {
      const q = filters.search.toLowerCase();
      items = items.filter((u) => u.email.toLowerCase().includes(q));
    }
    return { items, total: items.length, page, pageSize };
  }
}

export interface TestHarness {
  container: Container;
  userRepo: InMemoryUserRepository;
  passwords: IPasswordService;
  auditService: FakeAuditLogService;
}

/**
 * Build a container wired with fakes for infra and real security services, plus
 * one seeded user per role (password: "Password123!").
 */
export async function buildTestContainer(): Promise<TestHarness> {
  const config = makeTestConfig();
  const container = new Container({ defaultScope: 'Singleton' });

  container.bind(TYPES.Config).toConstantValue(config);
  container.bind(TYPES.Logger).toConstantValue(pino({ level: 'silent' }));
  container.bind(TYPES.PrismaService).toConstantValue(new FakePrismaService());
  container.bind(TYPES.RedisService).toConstantValue(new FakeRedisService());

  container.bind<IJwtService>(TYPES.JwtService).to(JwtService).inSingletonScope();
  container.bind<IPasswordService>(TYPES.PasswordService).to(BcryptPasswordService);
  container.bind<ITokenStore>(TYPES.TokenStore).toConstantValue(new InMemoryTokenStore());

  const auditService = new FakeAuditLogService();
  container.bind(TYPES.AuditLogService).toConstantValue(auditService);

  const userRepo = new InMemoryUserRepository();

  bindUsersModule(container);
  bindAuthModule(container);
  bindRolesModule(container);
  container.bind(TYPES.DepartmentAccessService).to(DepartmentAccessService).inSingletonScope();
  container.bind(TYPES.StorageService).to(LocalStorageService).inSingletonScope();
  container.bind(TYPES.IndexingQueue).to(BullMQIndexingQueue).inSingletonScope();
  container.bind(TYPES.AiGateway).to(AiGateway).inSingletonScope();
  container.load(departmentModule);
  container.load(documentModule);
  container.load(conversationModule);
  container.load(dashboardModule);
  container.load(analyticsModule);
  container.load(auditLogsModule);
  container.load(notificationModule);
  container.load(adminSettingsModule);
  container.load(onboardingModule);
  // Replace the Prisma repository (bound by the module) with the in-memory instance.
  container.rebind<IUserRepository>(TYPES.UserRepository).toConstantValue(userRepo);

  const passwords = container.get<IPasswordService>(TYPES.PasswordService);
  const hash = await passwords.hash('Password123!');
  userRepo.add(
    new UserEntity({
      id: 'u_employee',
      email: 'employee@optiagent.dev',
      passwordHash: hash,
      department: 'Engineering',
      isActive: true,
      role: Role.EMPLOYEE,
      createdAt: new Date(),
    }),
  );
  userRepo.add(
    new UserEntity({
      id: 'u_hr',
      email: 'hr.manager@optiagent.dev',
      passwordHash: hash,
      department: 'HR',
      isActive: true,
      role: Role.HR_MANAGER,
      createdAt: new Date(),
    }),
  );
  userRepo.add(
    new UserEntity({
      id: 'u_it_admin',
      email: 'it.admin@optiagent.dev',
      passwordHash: hash,
      department: 'IT',
      isActive: true,
      role: Role.IT_ADMIN,
      createdAt: new Date(),
    }),
  );

  return { container, userRepo, passwords, auditService };
}
