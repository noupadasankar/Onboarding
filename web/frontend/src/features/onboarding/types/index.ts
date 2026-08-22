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

export type TaskCategory = 'HR' | 'IT' | 'Finance' | 'Compliance' | 'General';

export interface Task {
  task_id: string;
  user_id: string;
  title: string;
  description: string;
  category?: TaskCategory;
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
  category?: TaskCategory;
  due_date?: string;
  priority?: TaskPriority;
  status?: TaskStatus;
}

export interface UpdateTaskRequest {
  title?: string;
  description?: string;
  category?: TaskCategory;
  status?: TaskStatus;
  priority?: TaskPriority;
  due_date?: string;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
}

export interface OnboardingOverview {
  totalTasks: number;
  completedTasks: number;
  inProgressTasks: number;
  pendingTasks: number;
  progressPercentage: number;
}

export interface Citation {
  filename?: string;
  page?: number | null;
  section?: string | null;
  score?: number | null;
  document_id?: string;
  chunk_id?: string;
  content?: string;
  metadata?: Record<string, unknown>;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  timestamp?: string;
}

export interface OnboardingChatRequest {
  question: string;
  conversation_id?: string;
  user_id?: string;
}

export interface OnboardingChatResponse {
  conversation_id: string;
  answer: string;
  citations: Citation[];
  model: string;
  provider: string;
  latency_ms: number;
  tasks_updated?: boolean;
  tasks?: Task[];
}

