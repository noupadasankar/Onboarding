/**
 * The login form validates with the SAME Zod schema the backend uses (imported
 * from @hr-onboarding/shared) — validation rules are never duplicated across the stack.
 */
export { loginSchema, type LoginInput } from '@hr-onboarding/shared';
