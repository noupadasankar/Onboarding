/**
 * AI Gateway — internal HTTP client that forwards requests to FastAPI.
 *
 * Security model (verbatim from architecture):
 *   Node.js forwards X-Internal-Token + X-User-Id + X-User-Role + X-User-Department.
 *   The AI service verifies the shared token via hmac.compare_digest.
 *   The browser never touches the AI service directly.
 */
import { inject, injectable } from 'inversify';
import type { AppConfig } from '../../config/env';
import { TYPES } from '../../core/di/types';
import { AppError } from '../../core/errors/app-error';
import { ErrorCode } from '@optiagent/shared';
import type { Logger } from 'pino';

export interface AiUserContext {
  userId: string;
  role: string;
  department?: string | null;
}

export interface AiIndexRequest {
  document_id: string;
  filename: string;
  storage_path: string;
  department?: string | null;
  mime_type: string;
  size_bytes: number;
  // Versioning: the document being indexed is always the current latest.
  version?: number;
  is_latest?: boolean;
  // Provenance — persisted into vector metadata for traceability/filtering.
  department_id?: string | null;
  uploaded_by?: string | null;
  uploaded_at?: string | null;
  document_status?: string | null;
}

export interface AiIndexResponse {
  status: string;
  chunk_count?: number;
  vector_count?: number;
  ai_document_id?: string;
}

export interface AiChatRequest {
  question: string;
  conversation_id?: string | null;
  department?: string | null;
  document_id?: string | null;
  top_k?: number;
  min_score?: number;
  stream?: boolean;
}

export interface AiChatResponse {
  conversation_id: string;
  answer: string;
  citations: Array<{
    filename: string;
    page?: number | null;
    section?: string | null;
    score?: number | null;
  }>;
  model: string;
  provider: string;
  latency_ms: number;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    estimated_cost_usd: number;
  };
}

export interface IAiGateway {
  indexDocument(req: AiIndexRequest, user: AiUserContext): Promise<AiIndexResponse>;
  chat(req: AiChatRequest, user: AiUserContext): Promise<AiChatResponse>;
  health(): Promise<{ status: string }>;
  /** Delete all ChromaDB vectors for a document (called when a new version supersedes it). */
  deleteDocumentVectors(documentId: string): Promise<{ vectors_deleted: number }>;
}

@injectable()
export class AiGateway implements IAiGateway {
  private readonly baseUrl: string;
  private readonly token: string;

  constructor(
    @inject(TYPES.Config) config: AppConfig,
    @inject(TYPES.Logger) private readonly log: Logger,
  ) {
    this.baseUrl = config.aiService.url;
    this.token = config.aiService.internalToken;
  }

  async indexDocument(req: AiIndexRequest, user: AiUserContext): Promise<AiIndexResponse> {
    const url = `${this.baseUrl}/api/v1/documents/index`;
    this.log.debug({ url, document_id: req.document_id }, 'ai_gateway:index');

    const resp = await this._fetch(url, {
      method: 'POST',
      body: JSON.stringify(req),
      user,
    });
    return resp as AiIndexResponse;
  }

  async chat(req: AiChatRequest, user: AiUserContext): Promise<AiChatResponse> {
    const url = `${this.baseUrl}/api/v1/chat`;
    this.log.debug({ url, question_len: req.question.length }, 'ai_gateway:chat');

    const resp = await this._fetch(url, {
      method: 'POST',
      body: JSON.stringify(req),
      user,
    });
    return resp as AiChatResponse;
  }

  async health(): Promise<{ status: string }> {
    const url = `${this.baseUrl}/api/v1/health`;
    const resp = await this._fetch(url, { method: 'GET' });
    return resp as { status: string };
  }

  async deleteDocumentVectors(documentId: string): Promise<{ vectors_deleted: number }> {
    const url = `${this.baseUrl}/api/v1/documents/${encodeURIComponent(documentId)}/vectors`;
    this.log.debug({ url, document_id: documentId }, 'ai_gateway:delete_vectors');
    // Vector deletion is a system-initiated operation (not user-facing).
    // We must still satisfy the AI service's authenticated_request dependency,
    // which requires X-User-Id and X-User-Role headers — pass a service identity.
    const resp = await this._fetch(url, {
      method: 'DELETE',
      user: { userId: 'system', role: 'SYSTEM' },
    });
    return resp as { vectors_deleted: number };
  }

  private async _fetch(
    url: string,
    opts: { method: string; body?: string; user?: AiUserContext },
  ): Promise<unknown> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Internal-Token': this.token,
    };
    if (opts.user) {
      headers['X-User-Id'] = opts.user.userId;
      headers['X-User-Role'] = opts.user.role;
      if (opts.user.department) headers['X-User-Department'] = opts.user.department;
    }

    let response: Response;
    try {
      response = await fetch(url, {
        method: opts.method,
        headers,
        body: opts.body,
        signal: AbortSignal.timeout(60_000),
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      this.log.error({ url, error: msg }, 'ai_gateway:network_error');
      throw new AppError(`AI service unreachable: ${msg}`, 502, ErrorCode.INTERNAL);
    }

    if (!response.ok) {
      const text = await response.text().catch(() => '');
      this.log.error({ url, status: response.status, body: text }, 'ai_gateway:error');
      throw new AppError(`AI service error ${response.status}: ${text}`, 502, ErrorCode.INTERNAL);
    }

    return response.json();
  }
}
