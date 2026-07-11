/**
 * Conversation application service.
 *
 * Owns the full chat orchestration on the Node side:
 *   1. Create or load a conversation.
 *   2. Persist the user message.
 *   3. Forward to AI gateway.
 *   4. Persist the assistant message + link AI conversation ID.
 *   5. Return the response.
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../../core/di/types';
import { ForbiddenError, NotFoundError } from '../../../core/errors/app-error';
import type { IAiGateway } from '../../../infrastructure/ai/ai-gateway';
import type {
  ConversationDetailDTO,
  ConversationDTO,
  IConversationRepository,
} from '../domain/conversation.repository';
import type { Logger } from 'pino';

export interface ChatInput {
  userId: string;
  userRole: string;
  userDepartment?: string | null;
  conversationId?: string | null;
  question: string;
  departmentHint?: string | null;
  topK?: number;
  minScore?: number;
  requestId?: string;
}

export interface ChatOutput {
  conversationId: string;
  answer: string;
  citations: Array<{
    filename: string;
    page?: number | null;
    section?: string | null;
    score?: number | null;
  }>;
  model: string;
  provider: string;
  latencyMs: number;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
    estimatedCostUsd: number;
  };
}

export interface IConversationService {
  list(userId: string, page: number, pageSize: number): Promise<{
    items: ConversationDTO[];
    total: number;
    page: number;
    pageSize: number;
  }>;
  getById(id: string, userId: string): Promise<ConversationDetailDTO>;
  chat(input: ChatInput): Promise<ChatOutput>;
  archive(id: string, userId: string): Promise<void>;
}

@injectable()
export class ConversationService implements IConversationService {
  constructor(
    @inject(TYPES.ConversationRepository) private readonly repo: IConversationRepository,
    @inject(TYPES.AiGateway) private readonly ai: IAiGateway,
    @inject(TYPES.Logger) private readonly log: Logger,
  ) {}

  async list(userId: string, page: number, pageSize: number) {
    return this.repo.list(userId, page, pageSize);
  }

  async getById(id: string, userId: string): Promise<ConversationDetailDTO> {
    const conv = await this.repo.findById(id);
    if (!conv) throw new NotFoundError('Conversation not found');
    if (conv.userId !== userId) throw new ForbiddenError('Access denied');
    return conv;
  }

  async chat(input: ChatInput): Promise<ChatOutput> {
    // 1. Resolve or create conversation
    let conv: ConversationDTO;
    if (input.conversationId) {
      const existing = await this.repo.findById(input.conversationId);
      if (!existing) throw new NotFoundError('Conversation not found');
      if (existing.userId !== input.userId) throw new ForbiddenError('Access denied');
      conv = existing;
    } else {
      conv = await this.repo.create({
        userId: input.userId,
        departmentHint: input.departmentHint ?? null,
        title: input.question.slice(0, 80),
      });
    }

    // 2. Persist user message
    await this.repo.appendMessage({
      conversationId: conv.id,
      role: 'user',
      content: input.question,
    });

    // 3. Call AI service
    const aiResp = await this.ai.chat(
      {
        question: input.question,
        conversation_id: conv.aiConversationId ?? null,
        department: input.departmentHint ?? null,
        top_k: input.topK ?? 5,
        min_score: input.minScore ?? 0.0,
        stream: false,
      },
      {
        userId: input.userId,
        role: input.userRole,
        department: input.userDepartment ?? null,
      },
    );

    // 4. Link AI conversation ID (idempotent after first turn)
    if (!conv.aiConversationId && aiResp.conversation_id) {
      await this.repo.linkAiConversation(conv.id, aiResp.conversation_id);
    }

    // 5. Persist assistant message
    await this.repo.appendMessage({
      conversationId: conv.id,
      role: 'assistant',
      content: aiResp.answer,
      model: aiResp.model,
      provider: aiResp.provider,
      promptTokens: aiResp.usage.prompt_tokens,
      completionTokens: aiResp.usage.completion_tokens,
      latencyMs: aiResp.latency_ms,
      citations: aiResp.citations,
    });

    this.log.info(
      {
        conversation_id: conv.id,
        tokens: aiResp.usage.total_tokens,
        latency_ms: aiResp.latency_ms,
      },
      'conversation:chat_complete',
    );

    return {
      conversationId: conv.id,
      answer: aiResp.answer,
      citations: aiResp.citations,
      model: aiResp.model,
      provider: aiResp.provider,
      latencyMs: aiResp.latency_ms,
      usage: {
        promptTokens: aiResp.usage.prompt_tokens,
        completionTokens: aiResp.usage.completion_tokens,
        totalTokens: aiResp.usage.total_tokens,
        estimatedCostUsd: aiResp.usage.estimated_cost_usd,
      },
    };
  }

  async archive(id: string, userId: string): Promise<void> {
    const conv = await this.repo.findById(id);
    if (!conv) throw new NotFoundError('Conversation not found');
    if (conv.userId !== userId) throw new ForbiddenError('Access denied');
    await this.repo.archive(id);
  }
}
