import { test, expect } from '@playwright/test';

test.describe('Smoke', () => {
  test('app responds with 200', async ({ request }) => {
    const r = await request.get('/');
    expect(r.status()).toBe(200);
  });

  test('no console errors on home load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/');
    await page.waitForLoadState('networkidle').catch(() => {});
    expect(errors.filter((e) => !e.includes('favicon'))).toEqual([]);
  });
});
