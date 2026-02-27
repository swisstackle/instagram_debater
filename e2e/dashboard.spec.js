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

    // Wait longer than the auto-refresh interval (5 seconds) to verify edit state
    // is NOT reset by the background auto-refresh
    await page.waitForTimeout(6000);

    // Textarea must still be visible and editable after auto-refresh fires
    await expect(page.locator('.editable-response')).toBeVisible();
    await expect(page.locator('.btn-save')).toBeVisible();
    
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

    // Now approve the edited response
    await page.locator('#main-actions-log_001 .btn-approve').click();

    // Wait for response to be updated
    await page.waitForTimeout(500);

    // Switch to approved filter to see the result
    await page.locator('[data-filter="approved"]').click();
    await page.waitForTimeout(200);

    // Check the approved response is shown and has correct status
    await expect(page.locator('.response-card')).toHaveCount(1);
    await expect(page.locator('.response-id')).toContainText('log_001');
    await expect(page.locator('.response-status')).toContainText('approved');

    // Ensure the edited response text appears in the approved section
    await expect(page.locator('.response-card .generated-response')).toContainText('Edited response text');

    // Verify via API that status is approved
    const resp2 = await request.get('/api/responses');
    const data2 = await resp2.json();
    expect(data2.responses[0].status).toBe('approved');
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

  test('displays mode toggle', async ({ page }) => {
    await page.goto('/');

    // The mode toggle should be visible
    await expect(page.locator('#auto-mode-toggle')).toBeVisible();
    await expect(page.locator('#mode-status-label')).toBeVisible();
  });

  test('mode toggle reflects current mode via API', async ({ page, request }) => {
    await page.goto('/');

    // Wait for mode to load via API
    await page.waitForResponse(resp => resp.url().includes('/api/mode') && resp.status() === 200);

    // Load initial mode from API
    const modeResponse = await request.get('/api/mode');
    const modeData = await modeResponse.json();

    // The toggle should reflect the current mode
    const toggle = page.locator('#auto-mode-toggle');
    if (modeData.auto_mode) {
      await expect(toggle).toBeChecked();
      await expect(page.locator('#mode-status-label')).toContainText('Auto');
    } else {
      await expect(toggle).not.toBeChecked();
      await expect(page.locator('#mode-status-label')).toContainText('Manual');
    }
  });

  test('can enable auto mode via toggle', async ({ page, request }) => {
    // Ensure auto mode is off initially
    await request.post('/api/mode', { data: { auto_mode: false } });

    await page.goto('/');

    // Wait for mode to load via API
    await page.waitForResponse(resp => resp.url().includes('/api/mode') && resp.status() === 200);

    // Toggle should be unchecked
    await expect(page.locator('#auto-mode-toggle')).not.toBeChecked();
    await expect(page.locator('#mode-status-label')).toContainText('Manual');

    // Click the toggle to enable auto mode and wait for the POST response
    const [modePostResponse] = await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/api/mode') && resp.request().method() === 'POST'),
      page.locator('#auto-mode-toggle').click(),
    ]);
    expect(modePostResponse.status()).toBe(200);

    // Label should update to Auto
    await expect(page.locator('#mode-status-label')).toContainText('Auto');

    // Verify via API
    const modeResponse = await request.get('/api/mode');
    const modeData = await modeResponse.json();
    expect(modeData.auto_mode).toBe(true);
  });

  test('can disable auto mode via toggle', async ({ page, request }) => {
    // Ensure auto mode is on initially
    await request.post('/api/mode', { data: { auto_mode: true } });

    await page.goto('/');

    // Wait for mode to load via API
    await page.waitForResponse(resp => resp.url().includes('/api/mode') && resp.status() === 200);

    // Toggle should be checked
    await expect(page.locator('#auto-mode-toggle')).toBeChecked();
    await expect(page.locator('#mode-status-label')).toContainText('Auto');

    // Click the toggle to disable auto mode and wait for the POST response
    const [modePostResponse] = await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/api/mode') && resp.request().method() === 'POST'),
      page.locator('#auto-mode-toggle').click(),
    ]);
    expect(modePostResponse.status()).toBe(200);

    // Label should update to Manual
    await expect(page.locator('#mode-status-label')).toContainText('Manual');

    // Verify via API
    const modeResponse = await request.get('/api/mode');
    const modeData = await modeResponse.json();
    expect(modeData.auto_mode).toBe(false);
  });

  // ================== ARTICLE MANAGER TESTS ==================

  test('displays article manager section', async ({ page }) => {
    await page.goto('/');

    // Article manager section should be visible
    await expect(page.locator('#article-manager')).toBeVisible();
    await expect(page.locator('#article-manager h2')).toContainText('Article Manager');

    // Add Article button should be present
    await expect(page.locator('button:has-text("+ Add Article")')).toBeVisible();
  });

  test('shows empty state when no articles', async ({ page }) => {
    await page.goto('/');

    // Article list should show empty message
    await expect(page.locator('#article-list')).toContainText('No articles yet.');
  });

  test('displays seeded articles', async ({ page, request }) => {
    await request.post('/api/test/seed', {
      data: {
        articles: [
          { id: 'art_001', title: 'Article One', content: '# Content', link: 'https://example.com/1' },
          { id: 'art_002', title: 'Article Two', content: '# Content 2', link: 'https://example.com/2' }
        ]
      }
    });

    await page.goto('/');

    // Both articles should be visible
    await expect(page.locator('.article-item')).toHaveCount(2);
    await expect(page.locator('.article-item-title').nth(0)).toContainText('Article One');
    await expect(page.locator('.article-item-title').nth(1)).toContainText('Article Two');
  });

  test('can add a new article', async ({ page, request }) => {
    await page.goto('/');

    // Click Add Article
    await page.locator('button:has-text("+ Add Article")').click();

    // Form should appear
    await expect(page.locator('#article-form')).toBeVisible();

    // Fill in form
    await page.locator('#article-form-title').fill('My New Article');
    await page.locator('#article-form-link').fill('https://example.com/new');
    await page.locator('#article-form-content').fill('# New Article\n\nSome content.');

    // Save
    await page.locator('#article-form button:has-text("Save")').click();

    // Wait for form to close and article to appear
    await expect(page.locator('#article-form')).not.toBeVisible();
    await expect(page.locator('.article-item-title')).toContainText('My New Article');

    // Verify via API
    const response = await request.get('/api/articles');
    const data = await response.json();
    expect(data.articles.length).toBe(1);
    expect(data.articles[0].title).toBe('My New Article');
    expect(data.articles[0].content).toBe('# New Article\n\nSome content.');
    expect(data.articles[0].link).toBe('https://example.com/new');
  });

  test('can edit an existing article', async ({ page, request }) => {
    await request.post('/api/test/seed', {
      data: {
        articles: [
          { id: 'art_001', title: 'Original Title', content: 'Original content', link: 'https://example.com/orig' }
        ]
      }
    });

    await page.goto('/');

    // Click Edit on the article
    await page.locator('.article-item .btn-edit').click();

    // Form should appear with existing values
    await expect(page.locator('#article-form')).toBeVisible();
    await expect(page.locator('#article-form-title')).toHaveValue('Original Title');
    await expect(page.locator('#article-form-link')).toHaveValue('https://example.com/orig');

    // Update title
    await page.locator('#article-form-title').clear();
    await page.locator('#article-form-title').fill('Updated Title');

    // Save
    await page.locator('#article-form button:has-text("Save")').click();

    // Form closes, updated title shows
    await expect(page.locator('#article-form')).not.toBeVisible();
    await expect(page.locator('.article-item-title')).toContainText('Updated Title');

    // Verify via API
    const response = await request.get('/api/articles');
    const data = await response.json();
    expect(data.articles[0].title).toBe('Updated Title');
  });

  test('can delete an article', async ({ page, request }) => {
    await request.post('/api/test/seed', {
      data: {
        articles: [
          { id: 'art_001', title: 'To Be Deleted', content: 'Content', link: 'https://example.com/del' }
        ]
      }
    });

    await page.goto('/');

    // Article should be visible
    await expect(page.locator('.article-item')).toHaveCount(1);

    // Click Delete and confirm the dialog
    page.once('dialog', dialog => dialog.accept());
    await page.locator('.article-item .btn-reject').click();

    // Article should be gone
    await expect(page.locator('.article-item')).toHaveCount(0);
    await expect(page.locator('#article-list')).toContainText('No articles yet.');

    // Verify via API
    const response = await request.get('/api/articles');
    const data = await response.json();
    expect(data.articles.length).toBe(0);
  });

  test('article form cancel hides form', async ({ page }) => {
    await page.goto('/');

    // Open form
    await page.locator('button:has-text("+ Add Article")').click();
    await expect(page.locator('#article-form')).toBeVisible();

    // Cancel
    await page.locator('#article-form button:has-text("Cancel")').click();

    // Form should be hidden
    await expect(page.locator('#article-form')).not.toBeVisible();
  });

  test('edit form shows full article content including special characters', async ({ page, request }) => {
    // Article content with double quotes, newlines, and other special characters
    // that break HTML data-attribute storage when content is not properly escaped.
    const fullContent = 'This article argues that "high-load" exercises cause harm.\n\n## Section 1\n\nEvidence shows a "significant" risk.\n\n## Section 2\n\nSee also: <https://example.com> & related work.';

    await request.post('/api/test/seed', {
      data: {
        articles: [
          { id: 'art_001', title: 'Full Content Article', content: fullContent, link: 'https://example.com/full' }
        ]
      }
    });

    await page.goto('/');

    // Click Edit on the article
    await page.locator('.article-item .btn-edit').click();

    // Form should appear with the FULL content preserved
    await expect(page.locator('#article-form')).toBeVisible();
    await expect(page.locator('#article-form-content')).toHaveValue(fullContent);
  });
});
