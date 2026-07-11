/**
 * Shared Zod schemas. Validation lives here once and is reused by the frontend
 * (React Hook Form resolver) and the backend (request validation middleware),
 * so rules can never diverge between client and server.
 */
import { z } from 'zod';
import { Role } from './roles.js';
import { paginationQuerySchema } from '../common/pagination.js';

/** Password policy — enforced identically on both ends. */
export const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .max(128, 'Password must be at most 128 characters');

export const loginSchema = z.object({
  email: z.string().trim().toLowerCase().email('Enter a valid email address'),
  password: passwordSchema,
});

export const registerSchema = z.object({
  email: z.string().trim().toLowerCase().email('Enter a valid email address'),
  password: passwordSchema,
  role: z.nativeEnum(Role),
  department: z.string().trim().min(1).max(100).optional(),
});

export const refreshSchema = z.object({
  refreshToken: z.string().min(1, 'refreshToken is required'),
});

/** Alias — identical to registerSchema; prefer this name in user-management contexts. */
export const createUserSchema = registerSchema;

/** PATCH /users/:id — all fields optional. */
export const updateUserSchema = z.object({
  role: z.nativeEnum(Role).optional(),
  department: z.string().trim().min(1).max(100).nullish(),
  isActive: z.boolean().optional(),
});

/** GET /users query parameters — extends pagination with optional filters. */
export const userListQuerySchema = paginationQuerySchema.extend({
  search: z.string().trim().min(1).max(255).optional(),
  role: z.nativeEnum(Role).optional(),
  isActive: z
    .enum(['true', 'false'])
    .transform((v) => v === 'true')
    .optional(),
});

/** Inferred types stay in lock-step with the schemas above. */
export type LoginInput = z.infer<typeof loginSchema>;
export type RegisterInput = z.infer<typeof registerSchema>;
export type CreateUserInput = z.infer<typeof createUserSchema>;
export type UpdateUserInput = z.infer<typeof updateUserSchema>;
export type UserListQuery = z.infer<typeof userListQuerySchema>;
export type RefreshInput = z.infer<typeof refreshSchema>;
