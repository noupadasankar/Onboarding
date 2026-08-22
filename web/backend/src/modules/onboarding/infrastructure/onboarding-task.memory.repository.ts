/** In-memory Onboarding Task repository (replace with Prisma for production). */
import { randomUUID } from 'crypto';
import type { OnboardingTask, CreateTaskInput, UpdateTaskInput, OnboardingTaskRepository } from '../domain/onboarding-task.entity';

const taskStore = new Map<string, OnboardingTask>();

export class InMemoryOnboardingTaskRepository implements OnboardingTaskRepository {
  async create(input: CreateTaskInput): Promise<OnboardingTask> {
    const now = new Date().toISOString();
    const task: OnboardingTask = {
      task_id: randomUUID(),
      user_id: input.user_id,
      title: input.title,
      description: input.description ?? '',
      status: 'pending',
      priority: input.priority ?? 'medium',
      due_date: input.due_date ?? null,
      created_at: now,
      updated_at: now,
      completed_at: null,
    };
    taskStore.set(task.task_id, task);
    return task;
  }

  async findByUserId(userId: string): Promise<OnboardingTask[]> {
    const tasks: OnboardingTask[] = [];
    for (const task of taskStore.values()) {
      if (task.user_id === userId) {
        tasks.push(task);
      }
    }
    // Sort by created_at descending
    return tasks.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }

  async findById(taskId: string): Promise<OnboardingTask | null> {
    return taskStore.get(taskId) ?? null;
  }

  async update(taskId: string, input: UpdateTaskInput): Promise<OnboardingTask | null> {
    const task = taskStore.get(taskId);
    if (!task) return null;

    const updated: OnboardingTask = {
      ...task,
      title: input.title ?? task.title,
      description: input.description ?? task.description,
      status: input.status ?? task.status,
      priority: input.priority ?? task.priority,
      due_date: input.due_date ?? task.due_date,
      updated_at: new Date().toISOString(),
      completed_at: input.status === 'completed' && task.status !== 'completed'
        ? new Date().toISOString()
        : task.completed_at,
    };
    taskStore.set(taskId, updated);
    return updated;
  }

  async delete(taskId: string): Promise<boolean> {
    return taskStore.delete(taskId);
  }
}
