import { test as base, type Page } from '@playwright/test';

interface TestFixtures {
  loginPage: Page;
  authenticatedPage: Page;
}

export const test = base.extend<TestFixtures>({
  loginPage: async ({ page }, use) => {
    await page.goto('/login');
    await use(page);
  },

  authenticatedPage: async ({ page }, use) => {
    // Login as employee (default demo account)
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'employee@optiagent.dev');
    await page.fill('[data-testid="password-input"]', 'Password123!');
    await page.click('[data-testid="login-submit"]');
    await page.waitForURL('/dashboard');
    await use(page);
  },
});

export { expect } from '@playwright/test';