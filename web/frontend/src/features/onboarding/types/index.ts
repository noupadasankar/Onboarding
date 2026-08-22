/** Onboarding feature types. */

export enum TaskStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
}

export enum TaskPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
}

export interface Task {
  task_id: string;
  user_id: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface CreateTaskRequest {
  title: string;
  description?: string;
  due_date?: string;
  priority?: TaskPriority;
}

export interface UpdateTaskRequest {
  title?: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  due_date?: string;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export interface Citation {
  document_id: string;
  chunk_id: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface OnboardingChatRequest {
  question: string;
  conversation_id?: string;
  user_id: string;
}

export interface OnboardingChatResponse {
  conversation_id: string;
  answer: string;
  citations: Citation[];
  model: string;
  provider: string;
  latency_ms: number;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  tasks_updated?: boolean;
}
