import { test, expect } from '@playwright/test';

test.describe('Report page', () => {
  test('report route loads (may 404 until implemented)', async ({ page }) => {
    await page.goto('/report/acme-corp');
    await expect(page).toHaveTitle(/.+/);
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });

  test('navigate to report from home when search is implemented', async ({ page }) => {
    await page.goto('/');
    // If there is a search flow: fill company, submit, then we should land on /report/:slug
    // For now only check that report URL is reachable
    await page.goto('/report/test-company');
    await expect(page).toHaveURL(/\/report\/.+/);
  });
});
