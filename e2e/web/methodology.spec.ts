import { test, expect } from '@playwright/test'

test('methodology page loads without auth', async ({ page }) => {
  await page.goto('/methodology')
  await expect(page.getByRole('heading', { name: /methodology/i })).toBeVisible()
})

test('verdict rubric section is visible', async ({ page }) => {
  await page.goto('/methodology')
  await expect(page.getByText(/how verdicts are scored/i)).toBeVisible()
})

test('data sources section lists SEC', async ({ page }) => {
  await page.goto('/methodology')
  await expect(page.getByText(/SEC EDGAR/i)).toBeVisible()
})
