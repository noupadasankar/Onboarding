/** Onboarding Task controller. */
import type { Request, Response, NextFunction } from 'express';
import type { OnboardingTaskService } from '../application/onboarding-task.service';
import type { CreateTaskInput, UpdateTaskInput } from '../domain/onboarding-task.entity';
import { AppError } from '../../../core/errors/app-error';

export class OnboardingTaskController {
  constructor(private readonly service: OnboardingTaskService) {}

  createTask = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const userId = req.user?.userId;
      if (!userId) throw new AppError('Unauthorized', 401);

      const input: CreateTaskInput = {
        user_id: userId,
        title: req.body.title,
        description: req.body.description,
        due_date: req.body.due_date,
        priority: req.body.priority,
      };

      const task = await this.service.createTask(input);
      res.status(201).json({ data: task, message: 'Task created successfully' });
    } catch (err) {
      next(err);
    }
  };

  getTasks = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const userId = req.user?.userId;
      if (!userId) throw new AppError('Unauthorized', 401);

      const tasks = await this.service.getTasks(userId);
      res.json({ data: tasks, total: tasks.length });
    } catch (err) {
      next(err);
    }
  };

  getTask = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const userId = req.user?.userId;
      if (!userId) throw new AppError('Unauthorized', 401);

      const task = await this.service.getTask(req.params.taskId);
      if (!task) throw new AppError('Task not found', 404);
      if (task.user_id !== userId) throw new AppError('Forbidden', 403);

      res.json({ data: task });
    } catch (err) {
      next(err);
    }
  };

  updateTask = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const userId = req.user?.userId;
      if (!userId) throw new AppError('Unauthorized', 401);

      const task = await this.service.getTask(req.params.taskId);
      if (!task) throw new AppError('Task not found', 404);
      if (task.user_id !== userId) throw new AppError('Forbidden', 403);

      const input: UpdateTaskInput = {
        title: req.body.title,
        description: req.body.description,
        status: req.body.status,
        priority: req.body.priority,
        due_date: req.body.due_date,
      };

      const updated = await this.service.updateTask(req.params.taskId, input);
      res.json({ data: updated, message: 'Task updated successfully' });
    } catch (err) {
      next(err);
    }
  };

  completeTask = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const userId = req.user?.userId;
      if (!userId) throw new AppError('Unauthorized', 401);

      const task = await this.service.getTask(req.params.taskId);
      if (!task) throw new AppError('Task not found', 404);
      if (task.user_id !== userId) throw new AppError('Forbidden', 403);

      const updated = await this.service.completeTask(req.params.taskId);
      res.json({ data: updated, message: 'Task marked as completed' });
    } catch (err) {
      next(err);
    }
  };

  deleteTask = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const userId = req.user?.userId;
      if (!userId) throw new AppError('Unauthorized', 401);

      const task = await this.service.getTask(req.params.taskId);
      if (!task) throw new AppError('Task not found', 404);
      if (task.user_id !== userId) throw new AppError('Forbidden', 403);

      await this.service.deleteTask(req.params.taskId);
      res.json({ message: 'Task deleted successfully' });
    } catch (err) {
      next(err);
    }
  };
}
