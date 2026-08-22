/** Onboarding Task controller. */
import type { Request, Response, NextFunction } from 'express';
import { inject, injectable } from 'inversify';
import { TYPES } from '../../../core/di/types';
import type { OnboardingTaskService } from '../application/onboarding-task.service';
import type { CreateTaskInput, UpdateTaskInput } from '../domain/onboarding-task.entity';
import { AppError } from '../../../core/errors/app-error';
import { ApiResponse } from '../../../core/http/api-response';
import { ErrorCode } from '@hr-onboarding/shared';
import type { IAiGateway } from '../../../infrastructure/ai/ai-gateway';

@injectable()
export class OnboardingTaskController {
  constructor(
    @inject(TYPES.OnboardingTaskService) private readonly service: OnboardingTaskService,
    @inject(TYPES.AiGateway) private readonly aiGateway: IAiGateway,
  ) {}

  /** Conversational chat endpoint for onboarding assistant. */
  chat = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const user = req.auth;
      if (!user) throw new AppError('Unauthorized', 401, ErrorCode.UNAUTHENTICATED);

      const { question, conversation_id } = req.body as {
        question: string;
        conversation_id?: string;
      };

      if (!question || typeof question !== 'string') {
        throw new AppError('Question is required', 400, ErrorCode.VALIDATION);
      }

      // Call AI service via AI Gateway
      const aiResponse = await this.aiGateway.chat(
        {
          question,
          conversation_id: conversation_id ?? null,
          department: user.role === 'EMPLOYEE' ? 'hr' : (user.role.toLowerCase().replace('_', '') || 'hr'),
        },
        {
          userId: user.id,
          role: user.role,
          department: user.role === 'EMPLOYEE' ? 'hr' : 'hr',
        },
      );

      // Fetch latest tasks for this user to return with response
      const latestTasks = await this.service.getTasks(user.id);

      ApiResponse.success(res, {
        answer: aiResponse.answer,
        citations: aiResponse.citations,
        conversation_id: aiResponse.conversation_id,
        tasks_updated: true,
        tasks: latestTasks,
        model: aiResponse.model,
        provider: aiResponse.provider,
        latency_ms: aiResponse.latency_ms,
      });
    } catch (err) {
      next(err);
    }
  };

  /** Get onboarding overview metrics. */
  getOverview = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const userId = req.auth?.id;
      if (!userId) throw new AppError('Unauthorized', 401, ErrorCode.UNAUTHENTICATED);

      const overview = await this.service.getOverview(userId);
      ApiResponse.success(res, overview);
    } catch (err) {
      next(err);
    }
  };

  /** Create a new onboarding task manually. */
  createTask = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const userId = req.auth?.id;
      if (!userId) throw new AppError('Unauthorized', 401, ErrorCode.UNAUTHENTICATED);

      const input: CreateTaskInput = {
        user_id: userId,
        title: req.body.title,
        description: req.body.description,
        category: req.body.category || 'HR',
        due_date: req.body.due_date,
        priority: req.body.priority || 'medium',
        status: req.body.status || 'pending',
      };

      const task = await this.service.createTask(input);
      ApiResponse.created(res, task);
    } catch (err) {
      next(err);
    }
  };

  /** Get all onboarding tasks for user. */
  getTasks = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const userId = req.auth?.id;
      if (!userId) throw new AppError('Unauthorized', 401, ErrorCode.UNAUTHENTICATED);

      const tasks = await this.service.getTasks(userId);
      ApiResponse.success(res, { tasks, total: tasks.length });
    } catch (err) {
      next(err);
    }
  };

  /** Get a specific task by id. */
  getTask = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const userId = req.auth?.id;
      if (!userId) throw new AppError('Unauthorized', 401, ErrorCode.UNAUTHENTICATED);

      const taskId = req.params.taskId;
      if (!taskId) throw new AppError('Task ID required', 400, ErrorCode.VALIDATION);

      const task = await this.service.getTask(taskId);
      if (!task) throw new AppError('Task not found', 404, ErrorCode.NOT_FOUND);
      if (task.user_id !== userId) throw new AppError('Forbidden', 403, ErrorCode.FORBIDDEN);

      ApiResponse.success(res, task);
    } catch (err) {
      next(err);
    }
  };

  /** Update task. */
  updateTask = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const userId = req.auth?.id;
      if (!userId) throw new AppError('Unauthorized', 401, ErrorCode.UNAUTHENTICATED);

      const taskId = req.params.taskId;
      if (!taskId) throw new AppError('Task ID required', 400, ErrorCode.VALIDATION);

      const task = await this.service.getTask(taskId);
      if (!task) throw new AppError('Task not found', 404, ErrorCode.NOT_FOUND);
      if (task.user_id !== userId) throw new AppError('Forbidden', 403, ErrorCode.FORBIDDEN);

      const input: UpdateTaskInput = {
        title: req.body.title,
        description: req.body.description,
        category: req.body.category,
        status: req.body.status,
        priority: req.body.priority,
        due_date: req.body.due_date,
      };

      const updated = await this.service.updateTask(taskId, input);
      ApiResponse.success(res, updated);
    } catch (err) {
      next(err);
    }
  };

  /** Complete task. */
  completeTask = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const userId = req.auth?.id;
      if (!userId) throw new AppError('Unauthorized', 401, ErrorCode.UNAUTHENTICATED);

      const taskId = req.params.taskId;
      if (!taskId) throw new AppError('Task ID required', 400, ErrorCode.VALIDATION);

      const task = await this.service.getTask(taskId);
      if (!task) throw new AppError('Task not found', 404, ErrorCode.NOT_FOUND);
      if (task.user_id !== userId) throw new AppError('Forbidden', 403, ErrorCode.FORBIDDEN);

      const updated = await this.service.completeTask(taskId);
      ApiResponse.success(res, updated);
    } catch (err) {
      next(err);
    }
  };

  /** Delete task. */
  deleteTask = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const userId = req.auth?.id;
      if (!userId) throw new AppError('Unauthorized', 401, ErrorCode.UNAUTHENTICATED);

      const taskId = req.params.taskId;
      if (!taskId) throw new AppError('Task ID required', 400, ErrorCode.VALIDATION);

      const task = await this.service.getTask(taskId);
      if (!task) throw new AppError('Task not found', 404, ErrorCode.NOT_FOUND);
      if (task.user_id !== userId) throw new AppError('Forbidden', 403, ErrorCode.FORBIDDEN);

      await this.service.deleteTask(taskId);
      ApiResponse.success(res, { message: 'Task deleted successfully' });
    } catch (err) {
      next(err);
    }
  };
}

