/**
 * Document DI container bindings.
 */
import { ContainerModule } from 'inversify';
import { TYPES } from '../../core/di/types';
import { DocumentPrismaRepository } from './infrastructure/document.prisma.repository';
import { DocumentService } from './application/document.service';
import { DocumentController } from './document.controller';
import type { IDocumentRepository } from './domain/document.repository';
import type { IDocumentService } from './application/document.service';

export const documentModule = new ContainerModule((bind) => {
  bind<IDocumentRepository>(TYPES.DocumentRepository)
    .to(DocumentPrismaRepository)
    .inSingletonScope();

  bind<IDocumentService>(TYPES.DocumentService)
    .to(DocumentService)
    .inSingletonScope();

  bind<DocumentController>(TYPES.DocumentController)
    .to(DocumentController)
    .inSingletonScope();
});
