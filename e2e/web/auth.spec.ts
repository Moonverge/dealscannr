import { test, expect } from '@playwright/test'

test('register and login flow', async ({ page }) => {
  await page.route('**/api/auth/login', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ token: 'fake-token' }),
    })
  })
  await page.goto('/login')
  await page.getByPlaceholder('email').fill('u@test.co')
  await page.getByPlaceholder(/password/i).fill('password12345')
  await page.getByRole('button', { name: 'Log in' }).click()
  await expect(page).toHaveURL(/\/dashboard/)
})

test('protected routes redirect to login', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/login/)
})
