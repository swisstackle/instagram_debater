import { test, expect } from '@playwright/test';

test.describe('Dashboard UI Tests', () => {
  test.beforeEach(async ({ request }) => {
    // Reset state before each test
    await request.post('/api/test/reset');
  });

  test('displays empty state when no responses', async ({ page }) => {
    await page.goto('/');
    
    // Check page title
    await expect(page.locator('h1')).toContainText('Instagram Debate Bot Dashboard');
    
    // Check empty state
    await expect(page.locator('.empty-state')).toBeVisible();
    await expect(page.locator('.empty-state')).toContainText('No responses found');
  });

  test('displays pending responses', async ({ page, request }) => {
    // Seed test data
    await request.post('/api/test/seed', {
      data: {
        audit_log: {
          version: '1.0',
          entries: [
            {
              id: 'log_001',
              comment_id: 'comment_123',
              comment_text: 'I think climate change is not real',
              generated_response: 'According to the article (§1.2), climate change is supported by scientific evidence.',
              citations_used: ['§1.2', '§3.1'],
              status: 'pending_review',
              timestamp: '2026-01-31T20:00:00Z',
              validation_passed: true,
              validation_errors: []
            }
          ]
        }
      }
    });

    await page.goto('/');
    
    // Check that response is displayed
    await expect(page.locator('.response-card')).toHaveCount(1);
    await expect(page.locator('.response-id')).toContainText('log_001');
    await expect(page.locator('.comment-text')).toContainText('I think climate change is not real');
    await expect(page.locator('.generated-response')).toContainText('According to the article');
    
    // Check citations
    await expect(page.locator('.citation-tag')).toHaveCount(2);
    
    // Check status badge
    await expect(page.locator('.response-status')).toContainText('pending review');
    
    // Check action buttons are visible
    await expect(page.locator('.btn-approve')).toBeVisible();
    await expect(page.locator('#main-actions-log_001 .btn-reject')).toBeVisible();
    await expect(page.locator('.btn-edit')).toBeVisible();
  });

  test('can approve a response', async ({ page, request }) => {
    // Seed test data
    await request.post('/api/test/seed', {
      data: {
        audit_log: {
          version: '1.0',
          entries: [
            {
              id: 'log_001',
              comment_id: 'comment_123',
              comment_text: 'Test comment',
              generated_response: 'Test response',
              citations_used: ['§1.2'],
              status: 'pending_review',
              timestamp: '2026-01-31T20:00:00Z',
              validation_passed: true,
              validation_errors: []
            }
          ]
        }
      }
    });

    await page.goto('/');
    
    // Click approve button
    await page.locator('.btn-approve').click();
    
    // Wait for response to be updated
    await page.waitForTimeout(500);
    
    // Switch to approved filter to see the result
    await page.locator('[data-filter="approved"]').click();
    
    // Wait for filter to apply
    await page.waitForTimeout(200);
    
    // Check status changed to approved
    await expect(page.locator('.response-status')).toContainText('approved');
    
    // Verify via API
    const response = await request.get('/api/responses');
    const data = await response.json();
    expect(data.responses[0].status).toBe('approved');
  });

  test('can reject a response with reason', async ({ page, request }) => {
    // Seed test data
    await request.post('/api/test/seed', {
      data: {
        audit_log: {
          version: '1.0',
          entries: [
            {
              id: 'log_001',
              comment_id: 'comment_123',
              comment_text: 'Test comment',
              generated_response: 'Test response',
              citations_used: ['§1.2'],
              status: 'pending_review',
              timestamp: '2026-01-31T20:00:00Z',
              validation_passed: true,
              validation_errors: []
            }
          ]
        }
      }
    });

    await page.goto('/');
    
    // Click reject button
    await page.locator('#main-actions-log_001 .btn-reject').click();
    
    // Rejection form should appear
    await expect(page.locator('.rejection-form')).toBeVisible();
    
    // Fill in reason
    await page.locator('.rejection-form textarea').fill('Response is too aggressive');
    
    // Click confirm reject
    await page.locator('.btn-confirm-reject').click();
    
    // Wait for update
    await page.waitForTimeout(500);
    
    // Switch to rejected filter
    await page.locator('[data-filter="rejected"]').click();
    
    // Check status changed to rejected
    await expect(page.locator('.response-status')).toContainText('rejected');
    
    // Verify rejection reason is displayed
    await expect(page.locator('.response-card')).toContainText('Response is too aggressive');
    
    // Verify via API
    const response = await request.get('/api/responses');
    const data = await response.json();
    expect(data.responses[0].status).toBe('rejected');
    expect(data.responses[0].rejection_reason).toBe('Response is too aggressive');
  });

  test('can edit and approve a response', async ({ page, request }) => {
    // Seed test data
    await request.post('/api/test/seed', {
      data: {
        audit_log: {
          version: '1.0',
          entries: [
            {
              id: 'log_001',
              comment_id: 'comment_123',
              comment_text: 'Test comment',
              generated_response: 'Original response text',
              citations_used: ['§1.2'],
              status: 'pending_review',
              timestamp: '2026-01-31T20:00:00Z',
              validation_passed: true,
              validation_errors: []
            }
          ]
        }
      }
    });

    await page.goto('/');
    
    // Click edit button
    await page.locator('.btn-edit').click();
    
    // Textarea should be visible
    await expect(page.locator('.editable-response')).toBeVisible();
    
    // Edit the text
    await page.locator('.editable-response').clear();
    await page.locator('.editable-response').fill('Edited response text');
    
    // Click save
    await page.locator('.btn-save').click();
    
    // Wait for update
    await page.waitForTimeout(500);
    
    // Verify text was updated
    await expect(page.locator('.generated-response')).toContainText('Edited response text');
    
    // Verify via API
    const response = await request.get('/api/responses');
    const data = await response.json();
    expect(data.responses[0].generated_response).toBe('Edited response text');
  });

  test('can filter responses by status', async ({ page, request }) => {
    // Seed test data with multiple responses
    await request.post('/api/test/seed', {
      data: {
        audit_log: {
          version: '1.0',
          entries: [
            {
              id: 'log_001',
              comment_id: 'comment_1',
              comment_text: 'Comment 1',
              generated_response: 'Response 1',
              citations_used: ['§1.2'],
              status: 'pending_review',
              timestamp: '2026-01-31T20:00:00Z',
              validation_passed: true,
              validation_errors: []
            },
            {
              id: 'log_002',
              comment_id: 'comment_2',
              comment_text: 'Comment 2',
              generated_response: 'Response 2',
              citations_used: ['§1.3'],
              status: 'approved',
              timestamp: '2026-01-31T20:01:00Z',
              validation_passed: true,
              validation_errors: []
            },
            {
              id: 'log_003',
              comment_id: 'comment_3',
              comment_text: 'Comment 3',
              generated_response: 'Response 3',
              citations_used: ['§1.4'],
              status: 'rejected',
              timestamp: '2026-01-31T20:02:00Z',
              validation_passed: true,
              validation_errors: [],
              rejection_reason: 'Not appropriate'
            }
          ]
        }
      }
    });

    await page.goto('/');
    
    // Initially should show only pending (1)
    await expect(page.locator('.response-card')).toHaveCount(1);
    await expect(page.locator('.response-id')).toContainText('log_001');
    
    // Click approved filter
    await page.locator('[data-filter="approved"]').click();
    await expect(page.locator('.response-card')).toHaveCount(1);
    await expect(page.locator('.response-id')).toContainText('log_002');
    
    // Click rejected filter
    await page.locator('[data-filter="rejected"]').click();
    await expect(page.locator('.response-card')).toHaveCount(1);
    await expect(page.locator('.response-id')).toContainText('log_003');
    
    // Click all filter
    await page.locator('[data-filter="all"]').click();
    await expect(page.locator('.response-card')).toHaveCount(3);
  });

  test('shows comment details and citations', async ({ page, request }) => {
    // Seed test data
    await request.post('/api/test/seed', {
      data: {
        audit_log: {
          version: '1.0',
          entries: [
            {
              id: 'log_001',
              comment_id: 'comment_123',
              comment_text: 'This is the original Instagram comment that needs a response',
              generated_response: 'This is the generated response with citations.',
              citations_used: ['§1.2', '§3.1', '§4.5'],
              status: 'pending_review',
              timestamp: '2026-01-31T20:00:00Z',
              validation_passed: true,
              validation_errors: []
            }
          ]
        }
      }
    });

    await page.goto('/');
    
    // Check comment text section
    const commentSection = page.locator('.response-section').filter({ hasText: 'Original Comment' });
    await expect(commentSection).toBeVisible();
    await expect(commentSection.locator('.comment-text')).toContainText('This is the original Instagram comment');
    
    // Check generated response section
    const responseSection = page.locator('.response-section').filter({ hasText: 'Generated Response' });
    await expect(responseSection).toBeVisible();
    await expect(responseSection.locator('.generated-response')).toContainText('This is the generated response');
    
    // Check citations section
    const citationsSection = page.locator('.response-section').filter({ hasText: 'Citations Used' });
    await expect(citationsSection).toBeVisible();
    
    // Check all citations are displayed
    await expect(page.locator('.citation-tag')).toHaveCount(3);
    await expect(page.locator('.citation-tag').nth(0)).toContainText('§1.2');
    await expect(page.locator('.citation-tag').nth(1)).toContainText('§3.1');
    await expect(page.locator('.citation-tag').nth(2)).toContainText('§4.5');
  });

  test('shows validation status', async ({ page, request }) => {
    // Seed test data with validation passed
    await request.post('/api/test/seed', {
      data: {
        audit_log: {
          version: '1.0',
          entries: [
            {
              id: 'log_001',
              comment_id: 'comment_123',
              comment_text: 'Test comment',
              generated_response: 'Test response',
              citations_used: ['§1.2'],
              status: 'pending_review',
              timestamp: '2026-01-31T20:00:00Z',
              validation_passed: true,
              validation_errors: []
            }
          ]
        }
      }
    });

    await page.goto('/');
    
    // Response should be visible (validation passed)
    await expect(page.locator('.response-card')).toBeVisible();
    await expect(page.locator('.response-id')).toContainText('log_001');
  });
});
