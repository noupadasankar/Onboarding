import { injectable } from 'inversify';
import { randomUUID } from 'crypto';
import type { OnboardingTask, CreateTaskInput, UpdateTaskInput, OnboardingTaskRepository } from '../domain/onboarding-task.entity';

const taskStore = new Map<string, OnboardingTask>();

function createDefaultSeedTasks(userId: string): OnboardingTask[] {
  const now = new Date();
  const d3: string = new Date(now.getTime() + 3 * 86400000).toISOString().split('T')[0]!;
  const d7: string = new Date(now.getTime() + 7 * 86400000).toISOString().split('T')[0]!;
  const d14: string = new Date(now.getTime() + 14 * 86400000).toISOString().split('T')[0]!;
  const d30: string = new Date(now.getTime() + 30 * 86400000).toISOString().split('T')[0]!;

  return [
    {
      task_id: randomUUID(),
      user_id: userId,
      title: 'Complete I-9 Employment Eligibility Verification',
      description: 'Upload identity and work authorization documents to the onboarding portal.',
      category: 'HR',
      status: 'in_progress',
      priority: 'high',
      due_date: d3,
      created_at: now.toISOString(),
      updated_at: now.toISOString(),
      completed_at: null,
    },
    {
      task_id: randomUUID(),
      user_id: userId,
      title: 'Set up 1Password & MFA Authentication',
      description: 'Install 1Password and configure Multi-Factor Authentication for company email and VPN.',
      category: 'IT',
      status: 'completed',
      priority: 'high',
      due_date: d3,
      created_at: now.toISOString(),
      updated_at: now.toISOString(),
      completed_at: now.toISOString(),
    },
    {
      task_id: randomUUID(),
      user_id: userId,
      title: 'Submit W-4 & Direct Deposit Details',
      description: 'Fill out payroll tax withholding and provide checking account routing number.',
      category: 'Finance',
      status: 'pending',
      priority: 'high',
      due_date: d7,
      created_at: now.toISOString(),
      updated_at: now.toISOString(),
      completed_at: null,
    },
    {
      task_id: randomUUID(),
      user_id: userId,
      title: 'Review OptiAgent Employee Handbook & Policies',
      description: 'Read the Code of Conduct, Leave Policy, and Remote Work guidelines.',
      category: 'Compliance',
      status: 'pending',
      priority: 'medium',
      due_date: d14,
      created_at: now.toISOString(),
      updated_at: now.toISOString(),
      completed_at: null,
    },
    {
      task_id: randomUUID(),
      user_id: userId,
      title: 'Schedule 30-Day Check-in with Manager',
      description: 'Set up an informal 30-day alignment meeting with your People Manager.',
      category: 'HR',
      status: 'pending',
      priority: 'medium',
      due_date: d30,
      created_at: now.toISOString(),
      updated_at: now.toISOString(),
      completed_at: null,
    },
  ];
}

@injectable()
export class InMemoryOnboardingTaskRepository implements OnboardingTaskRepository {
  private ensureSeeded(userId: string): void {
    const hasTasks = Array.from(taskStore.values()).some((t) => t.user_id === userId);
    if (!hasTasks) {
      const defaults = createDefaultSeedTasks(userId);
      defaults.forEach((t) => taskStore.set(t.task_id, t));
    }
  }

  async create(input: CreateTaskInput): Promise<OnboardingTask> {
    const now = new Date().toISOString();
    const task: OnboardingTask = {
      task_id: randomUUID(),
      user_id: input.user_id,
      title: input.title,
      description: input.description ?? '',
      category: input.category ?? 'HR',
      status: input.status ?? 'pending',
      priority: input.priority ?? 'medium',
      due_date: input.due_date ?? null,
      created_at: now,
      updated_at: now,
      completed_at: input.status === 'completed' ? now : null,
    };
    taskStore.set(task.task_id, task);
    return task;
  }

  async findByUserId(userId: string): Promise<OnboardingTask[]> {
    this.ensureSeeded(userId);
    const tasks: OnboardingTask[] = [];
    for (const task of taskStore.values()) {
      if (task.user_id === userId) {
        tasks.push(task);
      }
    }
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
      category: input.category ?? task.category,
      status: input.status ?? task.status,
      priority: input.priority ?? task.priority,
      due_date: input.due_date !== undefined ? input.due_date : task.due_date,
      updated_at: new Date().toISOString(),
      completed_at: input.status === 'completed' && task.status !== 'completed'
        ? new Date().toISOString()
        : input.status && input.status !== 'completed'
        ? null
        : task.completed_at,
    };
    taskStore.set(taskId, updated);
    return updated;
  }

  async delete(taskId: string): Promise<boolean> {
    return taskStore.delete(taskId);
  }
}

