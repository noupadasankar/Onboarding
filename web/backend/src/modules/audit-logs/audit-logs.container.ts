/**
 * Audit logs read module DI bindings. Wires the view service and controller
 * into the container. The write-side AuditLogService is bound separately in
 * the infrastructure layer and is not touched here.
 */
import { ContainerModule } from 'inversify';
import { TYPES } from '../../core/di/types';
import { AuditLogViewService, type IAuditLogViewService } from './audit-logs.service';
import { AuditLogViewController } from './audit-logs.controller';

export const auditLogsModule = new ContainerModule((bind) => {
  bind<IAuditLogViewService>(TYPES.AuditLogViewService)
    .to(AuditLogViewService)
    .inSingletonScope();

  bind<AuditLogViewController>(TYPES.AuditLogViewController)
    .to(AuditLogViewController)
    .inSingletonScope();
});
