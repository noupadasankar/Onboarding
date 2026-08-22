/** Onboarding-related types shared between frontend and backend. */
import { z } from 'zod';

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

export const TaskSchema = z.object({
  task_id: z.string().uuid(),
  user_id: z.string(),
  title: z.string().min(1).max(200),
  description: z.string().optional(),
  status: z.nativeEnum(TaskStatus).default(TaskStatus.PENDING),
  priority: z.nativeEnum(TaskPriority).default(TaskPriority.MEDIUM),
  due_date: z.string().optional(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  completed_at: z.string().datetime().optional(),
});

export type Task = z.infer<typeof TaskSchema>;

export const CreateTaskSchema = z.object({
  title: z.string().min(1).max(200),
  description: z.string().optional(),
  due_date: z.string().optional(),
  priority: z.nativeEnum(TaskPriority).default(TaskPriority.MEDIUM),
});

export type CreateTaskRequest = z.infer<typeof CreateTaskSchema>;

export const UpdateTaskSchema = z.object({
  title: z.string().min(1).max(200).optional(),
  description: z.string().optional(),
  status: z.nativeEnum(TaskStatus).optional(),
  priority: z.nativeEnum(TaskPriority).optional(),
  due_date: z.string().optional(),
});

export type UpdateTaskRequest = z.infer<typeof UpdateTaskSchema>;

export const TaskListResponseSchema = z.object({
  tasks: z.array(TaskSchema),
  total: z.number().int().nonnegative(),
});

export type TaskListResponse = z.infer<typeof TaskListResponseSchema>;

export const ChatMessageSchema = z.object({
  role: z.enum(['user', 'assistant']),
  content: z.string(),
  timestamp: z.string().datetime().optional(),
});

export type ChatMessage = z.infer<typeof ChatMessageSchema>;

export const OnboardingChatRequestSchema = z.object({
  question: z.string().min(1).max(4096),
  conversation_id: z.string().optional(),
  user_id: z.string(),
});

export type OnboardingChatRequest = z.infer<typeof OnboardingChatRequestSchema>;

export const OnboardingChatResponseSchema = z.object({
  conversation_id: z.string(),
  answer: z.string(),
  citations: z.array(z.object({
    document_id: z.string(),
    chunk_id: z.string(),
    content: z.string(),
    score: z.number(),
    metadata: z.record(z.unknown()),
  })),
  model: z.string(),
  provider: z.string(),
  latency_ms: z.number(),
  usage: z.object({
    prompt_tokens: z.number(),
    completion_tokens: z.number(),
    total_tokens: z.number(),
  }),
  tasks_updated: z.boolean().optional(),
});

export type OnboardingChatResponse = z.infer<typeof OnboardingChatResponseSchema>;