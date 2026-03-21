import { test, expect } from '@playwright/test'

test('public share route renders without auth', async ({ page }) => {
  await page.route('**/api/share/deadbeefdeadbeefdeadbeefdeadbeef', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        report: {
          verdict: 'PASS',
          confidence_score: 0.5,
          lane_coverage: 2,
          chunk_count: 4,
          sections: {
            executive_summary: { text: 'E', citations: [], status: 'preliminary' },
            legal_regulatory: { text: 'L', citations: [], status: 'preliminary' },
            engineering_health: { text: 'G', citations: [], status: 'preliminary' },
            hiring_trends: { text: 'H', citations: [], status: 'preliminary' },
            funding_news: { text: 'F', citations: [], status: 'preliminary' },
          },
          known_unknowns: ['x'],
          disclaimer: 'Disc.',
        },
        entity_name: 'Shared Co',
        scan_date: '2025-01-01T00:00:00+00:00',
      }),
    })
  })
  await page.goto('/share/deadbeefdeadbeefdeadbeefdeadbeef')
  await expect(page.getByText('PASS')).toBeVisible()
  await expect(page.getByText(/Powered by/)).toBeVisible()
})
