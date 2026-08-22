import { test, expect } from './fixtures';

test.describe('Chat Flow', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/chat');
    await expect(authenticatedPage.locator('text=Chat with OptiAgent')).toBeVisible();
  });

  test('should send message and receive response', async ({ authenticatedPage }) => {
    const messageInput = authenticatedPage.locator('[data-testid="chat-input"]');
    await messageInput.fill('Hello, how can you help me?');
    await authenticatedPage.click('[data-testid="chat-send"]');

    // Wait for user message to appear
    await expect(authenticatedPage.locator('text=Hello, how can you help me?')).toBeVisible();

    // Wait for assistant response (with timeout for AI processing)
    await expect(authenticatedPage.locator('[data-testid="assistant-message"]').first()).toBeVisible({ timeout: 30000 });
  });

  test('should show conversation history in sidebar', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('[data-testid="conversation-sidebar"]')).toBeVisible();
    await expect(authenticatedPage.locator('text=New conversation')).toBeVisible();
  });

  test('should create new conversation', async ({ authenticatedPage }) => {
    await authenticatedPage.click('[data-testid="new-conversation"]');
    await expect(authenticatedPage.locator('text=New conversation')).toBeVisible();
  });
});

test.describe('Document Upload Flow', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/documents');
    await expect(authenticatedPage.locator('text=Documents')).toBeVisible();
  });

  test('should upload a document', async ({ authenticatedPage }) => {
    await authenticatedPage.click('[data-testid="upload-document-button"]');
    await expect(authenticatedPage.locator('text=Upload Document')).toBeVisible();

    // Upload a test file
    const fileInput = authenticatedPage.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test-document.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4\n%Test document\n%%EOF'),
    });

    await authenticatedPage.click('[data-testid="upload-submit"]');

    // Wait for upload to complete
    await expect(authenticatedPage.locator('text=Document uploaded successfully')).toBeVisible({ timeout: 10000 });
  });

  test('should show document in list after upload', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('[data-testid="document-list"]')).toBeVisible();
  });

  test('should filter documents by status', async ({ authenticatedPage }) => {
    await authenticatedPage.selectOption('[data-testid="status-filter"]', 'INDEXED');
    await expect(authenticatedPage.locator('[data-testid="document-list"]')).toBeVisible();
  });
});