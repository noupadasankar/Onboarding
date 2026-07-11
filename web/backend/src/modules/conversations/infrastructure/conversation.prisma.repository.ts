/**
 * Prisma implementation of IConversationRepository.
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../../core/di/types';
import type { PrismaService } from '../../../infrastructure/database/prisma.service';
import type {
  AppendMessageInput,
  CitationDTO,
  ConversationDTO,
  ConversationDetailDTO,
  CreateConversationInput,
  IConversationRepository,
  MessageDTO,
} from '../domain/conversation.repository';

@injectable()
export class ConversationPrismaRepository implements IConversationRepository {
  constructor(
    @inject(TYPES.PrismaService) private readonly prisma: PrismaService,
  ) {}

  private mapConv(c: {
    id: string; title: string | null; userId: string;
    aiConversationId: string | null; departmentHint: string | null;
    selectedAgent: string | null; isActive: boolean;
    createdAt: Date; updatedAt: Date;
    _count?: { messages: number };
  }): ConversationDTO {
    return {
      id: c.id,
      title: c.title,
      userId: c.userId,
      aiConversationId: c.aiConversationId,
      departmentHint: c.departmentHint,
      selectedAgent: c.selectedAgent,
      isActive: c.isActive,
      messageCount: c._count?.messages ?? 0,
      createdAt: c.createdAt.toISOString(),
      updatedAt: c.updatedAt.toISOString(),
    };
  }

  private mapMsg(m: {
    id: string; conversationId: string; role: string; content: string;
    model: string | null; provider: string | null;
    promptTokens: number | null; completionTokens: number | null;
    latencyMs: number | null; citations: unknown; createdAt: Date;
  }): MessageDTO {
    return {
      id: m.id,
      conversationId: m.conversationId,
      role: m.role as MessageDTO['role'],
      content: m.content,
      model: m.model,
      provider: m.provider,
      promptTokens: m.promptTokens,
      completionTokens: m.completionTokens,
      latencyMs: m.latencyMs,
      citations: Array.isArray(m.citations) ? (m.citations as CitationDTO[]) : [],
      createdAt: m.createdAt.toISOString(),
    };
  }

  async list(userId: string, page: number, pageSize: number) {
    const where = { userId, isActive: true };
    const [total, rows] = await Promise.all([
      this.prisma.client.conversation.count({ where }),
      this.prisma.client.conversation.findMany({
        where,
        orderBy: { updatedAt: 'desc' },
        skip: (page - 1) * pageSize,
        take: pageSize,
        include: { _count: { select: { messages: true } } },
      }),
    ]);
    return { items: rows.map(this.mapConv), total, page, pageSize };
  }

  async findById(id: string): Promise<ConversationDetailDTO | null> {
    const row = await this.prisma.client.conversation.findUnique({
      where: { id },
      include: {
        _count: { select: { messages: true } },
        messages: { orderBy: { createdAt: 'asc' } },
      },
    });
    if (!row) return null;
    return {
      ...this.mapConv(row),
      messages: row.messages.map(this.mapMsg),
    };
  }

  async create(input: CreateConversationInput): Promise<ConversationDTO> {
    const row = await this.prisma.client.conversation.create({
      data: {
        userId: input.userId,
        departmentHint: input.departmentHint ?? null,
        title: input.title ?? null,
      },
      include: { _count: { select: { messages: true } } },
    });
    return this.mapConv(row);
  }

  async linkAiConversation(id: string, aiConversationId: string, selectedAgent?: string): Promise<void> {
    await this.prisma.client.conversation.update({
      where: { id },
      data: {
        aiConversationId,
        ...(selectedAgent ? { selectedAgent } : {}),
      },
    });
  }

  async appendMessage(input: AppendMessageInput): Promise<MessageDTO> {
    const row = await this.prisma.client.message.create({
      data: {
        conversationId: input.conversationId,
        role: input.role,
        content: input.content,
        model: input.model ?? null,
        provider: input.provider ?? null,
        promptTokens: input.promptTokens ?? null,
        completionTokens: input.completionTokens ?? null,
        latencyMs: input.latencyMs ?? null,
        citations: (input.citations ?? []) as object[],
      },
    });
    // Touch updatedAt on the parent conversation
    await this.prisma.client.conversation.update({
      where: { id: input.conversationId },
      data: { updatedAt: new Date() },
    });
    return this.mapMsg(row);
  }

  async archive(id: string): Promise<void> {
    await this.prisma.client.conversation.update({
      where: { id },
      data: { isActive: false },
    });
  }
}
