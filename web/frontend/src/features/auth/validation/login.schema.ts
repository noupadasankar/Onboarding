/**
 * The login form validates with the SAME Zod schema the backend uses (imported
 * from @optiagent/shared) — validation rules are never duplicated across the stack.
 */
export { loginSchema, type LoginInput } from '@optiagent/shared';
