/**
 * Zod schemas for user request validation. Sourced from the shared package so
 * frontend and backend are always in sync.
 */
import { z } from 'zod';
import {
  createUserSchema,
  updateUserSchema,
  userListQuerySchema,
} from '@hr-onboarding/shared';

export { createUserSchema, updateUserSchema, userListQuerySchema };

/** Validates that a route param is a well-formed UUID v4. */
export const uuidParamSchema = z.object({
  id: z.string().uuid('Invalid user ID'),
});
