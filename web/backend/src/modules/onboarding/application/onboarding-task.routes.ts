/** Onboarding Task routes. */
import { Router } from 'express';
import type { Container } from 'inversify';
import type { AuthMiddleware } from '../../../middleware/authenticate.middleware';
import { TYPES } from '../../../core/di/types';
import type { OnboardingTaskController } from './onboarding-task.controller';

export function createOnboardingRoutes(
  container: Container,
  authenticate: AuthMiddleware,
): Router {
  const router = Router();
  const controller = container.get<OnboardingTaskController>(TYPES.OnboardingTaskController);

  router.use(authenticate);

  // Chat endpoint
  router.post('/chat', controller.chat);

  // Overview endpoint
  router.get('/overview', controller.getOverview);

  // Task CRUD endpoints
  router.post('/tasks', controller.createTask);
  router.get('/tasks', controller.getTasks);
  router.get('/tasks/:taskId', controller.getTask);
  router.patch('/tasks/:taskId', controller.updateTask);
  router.patch('/tasks/:taskId/complete', controller.completeTask);
  router.delete('/tasks/:taskId', controller.deleteTask);

  return router;
}

