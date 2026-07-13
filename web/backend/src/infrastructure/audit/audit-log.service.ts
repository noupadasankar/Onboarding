/**
 * Cross-cutting audit log service. Any application service can inject this and
 * call log() to write an append-only entry. Non-fatal: a failure to write an
 * audit entry must never block the business operation.
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../core/di/types';
import type { Prisma } from '@prisma/client';
import type { PrismaService } from '../database/prisma.service';
import type { Logger } from '../../core/logging/logger';

export interface AuditEntry {
  userId?: string;
  action: string;
  resource?: string;
  metadata?: Record<string, unknown>;
  ipAddress?: string;
  requestId?: string;
}

export interface IAuditLogService {
  log(entry: AuditEntry): Promise<void>;
}

@injectable()
export class AuditLogService implements IAuditLogService {
  constructor(
    @inject(TYPES.PrismaService) private readonly prisma: PrismaService,
    @inject(TYPES.Logger) private readonly logger: Logger,
  ) {}

  async log(entry: AuditEntry): Promise<void> {
    try {
      await this.prisma.client.auditLog.create({
        data: {
          userId: entry.userId ?? null,
          action: entry.action,
          resource: entry.resource ?? null,
          metadata: (entry.metadata ?? undefined) as Prisma.InputJsonValue | undefined,
          ipAddress: entry.ipAddress ?? null,
          requestId: entry.requestId ?? null,
        },
      });
    } catch (err) {
      this.logger.warn({ err, entry }, 'Failed to write audit log entry');
    }
  }
}
