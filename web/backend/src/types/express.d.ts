/**
 * Express request augmentation. `req.auth` is populated by the authenticate
 * middleware and consumed by authorize + controllers. `res.locals.requestId`
 * is set by the request-id middleware.
 */
import type { Permission, Role } from '@optiagent/shared';

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Express {
    interface AuthenticatedUser {
      id: string;
      email: string;
      role: Role;
      permissions: Permission[];
    }

    interface Request {
      auth?: AuthenticatedUser;
    }

    interface Locals {
      requestId: string;
    }
  }
}

export {};
