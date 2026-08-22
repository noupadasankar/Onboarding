/** Onboarding Task domain entity. */
export interface OnboardingTask {
  task_id: string;
  user_id: string;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  priority: 'low' | 'medium' | 'high';
  due_date: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface CreateTaskInput {
  user_id: string;
  title: string;
  description?: string;
  due_date?: string;
  priority?: 'low' | 'medium' | 'high';
}

export interface UpdateTaskInput {
  title?: string;
  description?: string;
  status?: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  priority?: 'low' | 'medium' | 'high';
  due_date?: string;
}

export interface OnboardingTaskRepository {
  create(input: CreateTaskInput): Promise<OnboardingTask>;
  findByUserId(userId: string): Promise<OnboardingTask[]>;
  findById(taskId: string): Promise<OnboardingTask | null>;
  update(taskId: string, input: UpdateTaskInput): Promise<OnboardingTask | null>;
  delete(taskId: string): Promise<boolean>;
}
