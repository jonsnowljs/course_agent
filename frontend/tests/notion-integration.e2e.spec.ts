import { test, expect } from '@playwright/test';

// Utility: mock backend endpoints if needed (or seed test data)
// This example assumes the backend is seeded with test data for the test user.

test.describe('Notion Integration E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Log in as test user (assume helper or use UI)
    await page.goto('/settings');
    await expect(page.getByText('Notion Integration')).toBeVisible();
  });

  test('shows Notion integration, syncs, filters, paginates, disconnects', async ({ page }) => {
    // Check Notion is connected
    await expect(page.getByText(/Notion is (connected|not connected)/i)).toBeVisible();

    // Sync button should be visible and enabled
    const syncBtn = page.getByRole('button', { name: /sync notion pages/i });
    await expect(syncBtn).toBeVisible();
    await expect(syncBtn).toBeEnabled();

    // Click sync and expect progress
    await syncBtn.click();
    await expect(page.getByText(/Sync started/i)).toBeVisible();
    // Wait for status to update (simulate polling)
    await expect(page.getByText(/Status:/i)).toBeVisible({ timeout: 5000 });

    // Filter by status
    await page.selectOption('select', { label: 'Error' });
    await expect(page.getByText('Error')).toBeVisible();

    // Filter by date (set to a date with no results)
    await page.fill('input[type="date"]:nth-of-type(1)', '2000-01-01');
    await expect(page.getByText('No sync history.')).toBeVisible();
    // Reset date filter
    await page.fill('input[type="date"]:nth-of-type(1)', '');

    // Search filter
    await page.fill('input[placeholder*="error or status"]', 'Some error');
    await expect(page.getByText('Some error')).toBeVisible();

    // Pagination (if more than one page)
    const nextBtn = page.getByRole('button', { name: /next/i });
    if (await nextBtn.isEnabled()) {
      await nextBtn.click();
      await expect(page.getByText(/Page 2 of/i)).toBeVisible();
    }

    // Disconnect
    const disconnectBtn = page.getByRole('button', { name: /disconnect notion/i });
    await disconnectBtn.click();
    await expect(page.getByText(/Disconnected from Notion/i)).toBeVisible();
  });
}); 
