/**
 * Composition root. Assembles the InversifyJS container: constants (config,
 * logger), infrastructure, security, then each feature module's bindings. This is
 * the single place object graphs are wired — call sites never `new` their deps.
 */
import { Container } from 'inversify';
import { TYPES } from './types';
import type { AppConfig } from '../../config/env';
import { createLogger, type Logger } from '../logging/logger';

import { PrismaService } from '../../infrastructure/database/prisma.service';
import { RedisService } from '../../infrastructure/cache/redis.service';
import { JwtService, type IJwtService } from '../../infrastructure/security/jwt.service';
import {
  BcryptPasswordService,
  type IPasswordService,
} from '../../infrastructure/security/password.service';
import { RedisTokenStore, type ITokenStore } from '../../infrastructure/security/token-store';

import {
  AuditLogService,
  type IAuditLogService,
} from '../../infrastructure/audit/audit-log.service';

import { AiGateway, type IAiGateway } from '../../infrastructure/ai/ai-gateway';

import {
  DepartmentAccessService,
  type IDepartmentAccessService,
} from '../auth/department-access.service';

import { LocalStorageService } from '../../infrastructure/storage/local-storage.service';
import type { IStorageService } from '../../infrastructure/storage/storage.service';

import { InMemoryIndexingQueue } from '../../infrastructure/queue/in-memory-indexing-queue';
import type { IIndexingQueue } from '../../infrastructure/queue/indexing-queue';

import { bindAuthModule } from '../../modules/auth/auth.container';
import { bindUsersModule } from '../../modules/users/user.container';
import { bindRolesModule } from '../../modules/roles/roles.container';
import { departmentModule } from '../../modules/departments/department.container';
import { documentModule } from '../../modules/documents/document.container';
import { conversationModule } from '../../modules/conversations/conversation.container';
import { dashboardModule } from '../../modules/dashboard/dashboard.container';
import { analyticsModule } from '../../modules/analytics/analytics.container';
import { auditLogsModule } from '../../modules/audit-logs/audit-logs.container';
import { notificationModule } from '../../modules/notifications/notification.container';
import { adminSettingsModule } from '../../modules/admin-settings/admin-settings.container';

export function buildContainer(config: AppConfig): Container {
  const container = new Container({ defaultScope: 'Singleton' });

  // --- Constants (pre-built values) ---
  container.bind<AppConfig>(TYPES.Config).toConstantValue(config);
  container.bind<Logger>(TYPES.Logger).toConstantValue(createLogger(config));

  // --- Infrastructure ---
  container.bind<PrismaService>(TYPES.PrismaService).to(PrismaService).inSingletonScope();
  container.bind<RedisService>(TYPES.RedisService).to(RedisService).inSingletonScope();

  // --- Security ---
  container.bind<IJwtService>(TYPES.JwtService).to(JwtService).inSingletonScope();
  container
    .bind<IPasswordService>(TYPES.PasswordService)
    .to(BcryptPasswordService)
    .inSingletonScope();
  container.bind<ITokenStore>(TYPES.TokenStore).to(RedisTokenStore).inSingletonScope();

  // --- Infrastructure services ---
  container
    .bind<IAuditLogService>(TYPES.AuditLogService)
    .to(AuditLogService)
    .inSingletonScope();

  // --- AI Gateway ---
  container.bind<IAiGateway>(TYPES.AiGateway).to(AiGateway).inSingletonScope();

  // --- Authorization policy (role → department) ---
  container
    .bind<IDepartmentAccessService>(TYPES.DepartmentAccessService)
    .to(DepartmentAccessService)
    .inSingletonScope();

  // --- Storage (swap LocalStorageService for S3/Azure/MinIO here) ---
  container
    .bind<IStorageService>(TYPES.StorageService)
    .to(LocalStorageService)
    .inSingletonScope();

  // --- Indexing queue (swap for Redis/BullMQ-backed impl to scale out) ---
  container
    .bind<IIndexingQueue>(TYPES.IndexingQueue)
    .to(InMemoryIndexingQueue)
    .inSingletonScope();

  // --- Feature modules ---
  bindUsersModule(container);
  bindAuthModule(container);
  bindRolesModule(container);
  container.load(departmentModule);
  container.load(documentModule);
  container.load(conversationModule);
  container.load(dashboardModule);
  container.load(analyticsModule);
  container.load(auditLogsModule);
  container.load(notificationModule);
  container.load(adminSettingsModule);

  return container;
}

