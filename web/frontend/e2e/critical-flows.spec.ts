import { test, expect } from './fixtures';

test.describe('Authentication Flow', () => {
  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('h1')).toContainText('Sign in');

    await page.fill('input[type="email"]', 'employee@optiagent.dev');
    await page.fill('input[type="password"]', 'Password123!');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('text=Dashboard')).toBeVisible();
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="email"]', 'invalid@optiagent.dev');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    await expect(page.locator('text=Invalid email or password')).toBeVisible();
  });

  test('should redirect to login when accessing protected route unauthenticated', async ({ page }) => {
    await page.goto('/users');
    await expect(page).toHaveURL('/login');
  });

  test('should logout successfully', async ({ authenticatedPage }) => {
    // Click user menu and logout
    await authenticatedPage.click('[data-testid="user-menu-button"]');
    await authenticatedPage.click('[data-testid="logout-button"]');

    await expect(authenticatedPage).toHaveURL('/login');
  });
});

test.describe('Dashboard', () => {
  test('should display employee dashboard', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Welcome back')).toBeVisible();
    await expect(authenticatedPage.locator('text=Recent Activity')).toBeVisible();
  });

  test('should show role-specific widgets', async ({ authenticatedPage }) => {
    // Employee should see basic widgets
    await expect(authenticatedPage.locator('text=Quick Actions')).toBeVisible();
  });
});

test.describe('Chat Flow', () => {
  test('should send a message and receive response', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/chat');
    await expect(authenticatedPage.locator('text=New Conversation')).toBeVisible();

    // Start new conversation
    await authenticatedPage.click('text=New Conversation');
    await authenticatedPage.fill('[data-testid="chat-input"]', 'Hello, what can you help me with?');
    await authenticatedPage.click('[data-testid="send-button"]');

    // Wait for user message to appear
    await expect(authenticatedPage.locator('text=Hello, what can you help me with?')).toBeVisible();

    // Wait for assistant response (with timeout for AI processing)
    await expect(authenticatedPage.locator('[data-testid="assistant-message"]').last()).toBeVisible({ timeout: 30000 });
  });

  test('should show conversation history in sidebar', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/chat');
    await expect(authenticatedPage.locator('[data-testid="conversation-sidebar"]')).toBeVisible();
  });
});

test.describe('Document Upload Flow', () => {
  test('should upload a document successfully', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/documents');
    await expect(authenticatedPage.locator('text=Documents')).toBeVisible();

    // Click upload button
    await authenticatedPage.click('[data-testid="upload-button"]');
    await expect(authenticatedPage.locator('text=Upload Document')).toBeVisible();

    // Upload file
    const filePath = 'tests/fixtures/sample.pdf';
    await authenticatedPage.setInputFiles('input[type="file"]', filePath);
    await authenticatedPage.selectOption('select[name="department"]', 'hr');
    await authenticatedPage.click('button:has-text("Upload")');

    // Wait for upload to complete
    await expect(authenticatedPage.locator('text=Document uploaded successfully')).toBeVisible({ timeout: 10000 });
  });

  test('should show document in list after upload', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/documents');
    await expect(authenticatedPage.locator('table tbody tr').first()).toBeVisible();
  });
});

test.describe('Navigation & Permissions', () => {
  test('should hide admin menu items for employee role', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await expect(authenticatedPage.locator('text=Admin Settings')).not.toBeVisible();
    await expect(authenticatedPage.locator('text=Users')).not.toBeVisible();
  });

  test('should show 403 for unauthorized direct URL access', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/admin/settings');
    await expect(authenticatedPage.locator('text=403 — Forbidden')).toBeVisible();
  });
});