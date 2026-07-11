/**
 * Conversation routes.
 */
import { Router } from 'express';
import type { Container } from 'inversify';
import { z } from 'zod';
import { TYPES } from '../../core/di/types';
import { validate } from '../../middleware/validate.middleware';
import type { ConversationController } from './conversation.controller';
import type { AuthMiddleware } from '../../middleware/authenticate.middleware';

const chatBody = z.object({
  question: z.string().min(2).max(4096),
  conversationId: z.string().uuid().optional(),
  departmentHint: z.enum(['hr', 'finance', 'it', 'general']).optional(),
  topK: z.coerce.number().int().min(1).max(20).optional(),
  minScore: z.coerce.number().min(0).max(1).optional(),
});

export function createConversationRoutes(
  container: Container,
  authenticate: AuthMiddleware,
): Router {
  const router = Router();
  const ctrl = container.get<ConversationController>(TYPES.ConversationController);

  router.use(authenticate);

  router.get('/', ctrl.list);
  router.get('/:id', ctrl.getById);
 router.post('/chat', validate(chatBody), ctrl.chat);
  router.delete('/:id', ctrl.archive);

  return router;
}
