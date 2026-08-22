/**
 * Auth request schemas. Re-exports the shared Zod schemas so the module has a
 * single import surface; validation rules themselves live in @hr-onboarding/shared
 * and are reused by the frontend (no duplicate validation).
 */
export { loginSchema, refreshSchema } from '@hr-onboarding/shared';
