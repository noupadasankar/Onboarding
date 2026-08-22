/** Onboarding Task routes. */
import { Router, type RequestHandler } from 'express';
import type { Container } from 'inversify';
import type { IAuthenticate } from '../../../middleware/authenticate.middleware';
import { TYPES } from '../../../core/di/types';

export function createOnboardingRoutes(
  container: Container,
  authenticate: IAuthenticate
): Router {
  const router = Router();
  const controller = container.get<OnboardingTaskController>(TYPES.OnboardingTaskController);

  // All routes require authentication
  router.use(authenticate as RequestHandler);

  router.post('/tasks', controller.createTask);
  router.get('/tasks', controller.getTasks);
  router.get('/tasks/:taskId', controller.getTask);
  router.patch('/tasks/:taskId', controller.updateTask);
  router.patch('/tasks/:taskId/complete', controller.completeTask);
  router.delete('/tasks/:taskId', controller.deleteTask);

  return router;
}

// Type for the controller (will be registered in container)
import type { OnboardingTaskController } from '../application/onboarding-task.controller';
