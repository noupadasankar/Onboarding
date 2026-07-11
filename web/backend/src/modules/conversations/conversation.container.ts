/**
 * Conversation DI container bindings.
 */
import { ContainerModule } from 'inversify';
import { TYPES } from '../../core/di/types';
import { ConversationPrismaRepository } from './infrastructure/conversation.prisma.repository';
import { ConversationService } from './application/conversation.service';
import { ConversationController } from './conversation.controller';
import type { IConversationRepository } from './domain/conversation.repository';
import type { IConversationService } from './application/conversation.service';

export const conversationModule = new ContainerModule((bind) => {
  bind<IConversationRepository>(TYPES.ConversationRepository)
    .to(ConversationPrismaRepository)
    .inSingletonScope();

  bind<IConversationService>(TYPES.ConversationService)
    .to(ConversationService)
    .inSingletonScope();

  bind<ConversationController>(TYPES.ConversationController)
    .to(ConversationController)
    .inSingletonScope();
});
