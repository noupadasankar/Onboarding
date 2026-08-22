import { test, expect } from './fixtures';

test.describe('Authentication Flow', () => {
  test('should show login page on unauthenticated access', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/);
  });

  test('should login successfully with valid credentials', async ({ loginPage }) => {
    await loginPage.fill('[data-testid="email-input"]', 'employee@optiagent.dev');
    await loginPage.fill('[data-testid="password-input"]', 'Password123!');
    await loginPage.click('[data-testid="login-submit"]');
    await expect(loginPage).toHaveURL(/\/dashboard/);
  });

  test('should show error with invalid credentials', async ({ loginPage }) => {
    await loginPage.fill('[data-testid="email-input"]', 'wrong@optiagent.dev');
    await loginPage.fill('[data-testid="password-input"]', 'wrongpassword');
    await loginPage.click('[data-testid="login-submit"]');
    await expect(loginPage.locator('[data-testid="login-error"]')).toBeVisible();
  });

  test('should show error with empty fields', async ({ loginPage }) => {
    await loginPage.click('[data-testid="login-submit"]');
    await expect(loginPage.locator('text=Email is required')).toBeVisible();
    await expect(loginPage.locator('text=Password is required')).toBeVisible();
  });
});

test.describe('Dashboard Access', () => {
  test('should display employee dashboard for employee role', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Employee Dashboard')).toBeVisible();
  });

  test('should show navigation sidebar', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Dashboard')).toBeVisible();
    await expect(authenticatedPage.locator('text=Chat')).toBeVisible();
    await expect(authenticatedPage.locator('text=Documents')).toBeVisible();
    await expect(authenticatedPage.locator('text=Profile')).toBeVisible();
  });

  test('should NOT show admin-only navigation for employee', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Users')).not.toBeVisible();
    await expect(authenticatedPage.locator('text=Admin Settings')).not.toBeVisible();
  });
});