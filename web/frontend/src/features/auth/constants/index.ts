/** localStorage key under which the auth session is persisted across reloads. */
export const AUTH_STORAGE_KEY = 'optiagent.auth';

/** Demo credentials surfaced on the login screen for the capstone walkthrough. */
export const DEMO_CREDENTIALS = [
  { label: 'HR Manager', email: 'hr.manager@optiagent.dev' },
  { label: 'Finance Admin', email: 'finance.admin@optiagent.dev' },
  { label: 'IT Admin', email: 'it.admin@optiagent.dev' },
  { label: 'Employee', email: 'employee@optiagent.dev' },
] as const;

export const DEMO_PASSWORD = 'Password123!';
