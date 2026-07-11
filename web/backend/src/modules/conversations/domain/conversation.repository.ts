/**
 * Conversation + Message domain types and repository interface.
 */
export type MessageRole = 'user' | 'assistant' | 'system';

export interface CitationDTO {
  filename: string;
  page?: number | null;
  section?: string | null;
  score?: number | null;
}

export interface MessageDTO {
  id: string;
  conversationId: string;
  role: MessageRole;
  content: string;
  model: string | null;
  provider: string | null;
  promptTokens: number | null;
  completionTokens: number | null;
  latencyMs: number | null;
  citations: CitationDTO[];
  createdAt: string;
}

export interface ConversationDTO {
  id: string;
  title: string | null;
  userId: string;
  aiConversationId: string | null;
  departmentHint: string | null;
  selectedAgent: string | null;
  isActive: boolean;
  messageCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface ConversationDetailDTO extends ConversationDTO {
  messages: MessageDTO[];
}

export interface CreateConversationInput {
  userId: string;
  departmentHint?: string | null;
  title?: string | null;
}

export interface AppendMessageInput {
  conversationId: string;
  role: MessageRole;
  content: string;
  model?: string | null;
  provider?: string | null;
  promptTokens?: number | null;
  completionTokens?: number | null;
  latencyMs?: number | null;
  citations?: CitationDTO[];
}

export interface IConversationRepository {
  list(userId: string, page: number, pageSize: number): Promise<{
    items: ConversationDTO[];
    total: number;
    page: number;
    pageSize: number;
  }>;
  findById(id: string): Promise<ConversationDetailDTO | null>;
  create(input: CreateConversationInput): Promise<ConversationDTO>;
  linkAiConversation(id: string, aiConversationId: string, selectedAgent?: string): Promise<void>;
  appendMessage(input: AppendMessageInput): Promise<MessageDTO>;
  archive(id: string): Promise<void>;
}
