/** Onboarding Task service. */
import type { OnboardingTask, CreateTaskInput, UpdateTaskInput, OnboardingTaskRepository } from '../domain/onboarding-task.entity';

export class OnboardingTaskService {
  constructor(private readonly repo: OnboardingTaskRepository) {}

  async createTask(input: CreateTaskInput): Promise<OnboardingTask> {
    return this.repo.create(input);
  }

  async getTasks(userId: string): Promise<OnboardingTask[]> {
    return this.repo.findByUserId(userId);
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
