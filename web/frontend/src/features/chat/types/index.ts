export interface CitationDTO {
  filename: string;
  page?: number | null;
  section?: string | null;
  score?: number | null;
}

export interface MessageDTO {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  model?: string | null;
  promptTokens?: number | null;
  completionTokens?: number | null;
  latencyMs?: number | null;
  citations?: CitationDTO[] | null;
  createdAt: string;
}

export interface ConversationDTO {
  id: string;
  title: string | null;
  userId: string;
  departmentHint: string | null;
  selectedAgent: string | null;
  isActive: boolean;
  messageCount?: number;
  createdAt: string;
  updatedAt: string;
}

export interface ConversationDetailDTO extends ConversationDTO {
  messages: MessageDTO[];
}

export interface ChatRequest {
  question: string;
  conversationId?: string;
  departmentHint?: string;
  topK?: number;
}

export interface ChatResponse {
  conversationId: string;
  answer: string;
  citations: CitationDTO[];
  model: string;
  latencyMs: number;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

export interface ConversationListResult {
  items: ConversationDTO[];
  total: number;
  page: number;
  pageSize: number;
}
