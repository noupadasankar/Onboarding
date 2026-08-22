import { inject, injectable } from 'inversify';
import { TYPES } from '../../../core/di/types';
import type {
  OnboardingTask,
  CreateTaskInput,
  UpdateTaskInput,
  OnboardingOverview,
  OnboardingTaskRepository,
} from '../domain/onboarding-task.entity';

@injectable()
export class OnboardingTaskService {
  constructor(
    @inject(TYPES.OnboardingTaskRepository) private readonly repo: OnboardingTaskRepository,
  ) {}

  async createTask(input: CreateTaskInput): Promise<OnboardingTask> {
    return this.repo.create(input);
  }

  async getTasks(userId: string): Promise<OnboardingTask[]> {
    return this.repo.findByUserId(userId);
  }

  async getOverview(userId: string): Promise<OnboardingOverview> {
    const tasks = await this.repo.findByUserId(userId);
    const total = tasks.length;
    const completed = tasks.filter((t) => t.status === 'completed').length;
    const inProgress = tasks.filter((t) => t.status === 'in_progress').length;
    const pending = tasks.filter((t) => t.status === 'pending').length;
    const progressPercentage = total > 0 ? Math.round((completed / total) * 100) : 0;

    return {
      totalTasks: total,
      completedTasks: completed,
      inProgressTasks: inProgress,
      pendingTasks: pending,
      progressPercentage,
    };
  }

  async getTask(taskId: string): Promise<OnboardingTask | null> {
    return this.repo.findById(taskId);
  }

  async updateTask(taskId: string, input: UpdateTaskInput): Promise<OnboardingTask | null> {
    return this.repo.update(taskId, input);
  }

  async deleteTask(taskId: string): Promise<boolean> {
    return this.repo.delete(taskId);
  }

  async completeTask(taskId: string): Promise<OnboardingTask | null> {
    return this.repo.update(taskId, { status: 'completed' });
  }
}

