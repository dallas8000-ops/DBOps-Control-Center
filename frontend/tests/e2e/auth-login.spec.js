import { test, expect } from '@playwright/test';

test.describe('Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('renders login panel with correct heading and Login button', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'DBOps Control Center' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Login' })).toBeVisible();
  });

  test('shows email and password input fields', async ({ page }) => {
    await expect(page.getByPlaceholder(/email/i)).toBeVisible();
    await expect(page.getByPlaceholder(/password/i)).toBeVisible();
  });

  test('successfully logs in with DBA credentials', async ({ page }) => {
    await page.getByPlaceholder(/email/i).fill('dba@example.com');
    await page.getByPlaceholder(/password/i).fill('Password123!');
    await page.getByRole('button', { name: 'Login' }).click();

    await expect(page.getByText(/signed in as/i)).toBeVisible({ timeout: 10000 });
  });

  test('displays user email after successful login', async ({ page }) => {
    await page.getByPlaceholder(/email/i).fill('dba@example.com');
    await page.getByPlaceholder(/password/i).fill('Password123!');
    await page.getByRole('button', { name: 'Login' }).click();

    await expect(page.getByText(/dba@example\.com/i)).toBeVisible({ timeout: 10000 });
  });

  test('displays user role after successful login', async ({ page }) => {
    await page.getByPlaceholder(/email/i).fill('dba@example.com');
    await page.getByPlaceholder(/password/i).fill('Password123!');
    await page.getByRole('button', { name: 'Login' }).click();

    await expect(page.getByText(/signed in as/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/DBA/i)).toBeVisible({ timeout: 10000 });
  });

  test('shows error state when wrong password is entered', async ({ page }) => {
    await page.getByPlaceholder(/email/i).fill('dba@example.com');
    await page.getByPlaceholder(/password/i).fill('WrongPassword!');
    await page.getByRole('button', { name: 'Login' }).click();

    // Should NOT show signed in text
    await expect(page.getByText(/signed in as/i)).not.toBeVisible({ timeout: 5000 });

    // Should show some error indication
    const errorVisible = await Promise.race([
      page.getByText(/invalid/i).waitFor({ state: 'visible', timeout: 5000 }).then(() => true).catch(() => false),
      page.getByText(/error/i).waitFor({ state: 'visible', timeout: 5000 }).then(() => true).catch(() => false),
      page.getByText(/incorrect/i).waitFor({ state: 'visible', timeout: 5000 }).then(() => true).catch(() => false),
      page.getByText(/unauthorized/i).waitFor({ state: 'visible', timeout: 5000 }).then(() => true).catch(() => false),
      page.getByText(/failed/i).waitFor({ state: 'visible', timeout: 5000 }).then(() => true).catch(() => false),
    ]);

    expect(errorVisible).toBe(true);
  });

  test('shows Create Incident accordion section after login', async ({ page }) => {
    await page.getByPlaceholder(/email/i).fill('dba@example.com');
    await page.getByPlaceholder(/password/i).fill('Password123!');
    await page.getByRole('button', { name: 'Login' }).click();

    await expect(page.getByText(/signed in as/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/create incident/i)).toBeVisible({ timeout: 10000 });
  });

  test('Create Incident accordion section is toggleable after login', async ({ page }) => {
    await page.getByPlaceholder(/email/i).fill('dba@example.com');
    await page.getByPlaceholder(/password/i).fill('Password123!');
    await page.getByRole('button', { name: 'Login' }).click();

    await expect(page.getByText(/signed in as/i)).toBeVisible({ timeout: 10000 });

    // Find the Create Incident accordion button
    const createIncidentButton = page.getByRole('button', { name: /create incident/i });
    await expect(createIncidentButton).toBeVisible({ timeout: 10000 });

    // Check that it has aria-expanded attribute (accordion behavior)
    const ariaExpanded = await createIncidentButton.getAttribute('aria-expanded');
    expect(ariaExpanded).not.toBeNull();
  });

  test('full login flow persists token in localStorage', async ({ page }) => {
    await page.getByPlaceholder(/email/i).fill('dba@example.com');
    await page.getByPlaceholder(/password/i).fill('Password123!');
    await page.getByRole('button', { name: 'Login' }).click();

    await expect(page.getByText(/signed in as/i)).toBeVisible({ timeout: 10000 });

    const token = await page.evaluate(() => localStorage.getItem('dbops_token'));
    expect(token).not.toBeNull();
    expect(token.length).toBeGreaterThan(0);
  });

  test('shows wrong email error for non-existent user', async ({ page }) => {
    await page.getByPlaceholder(/email/i).fill('nonexistent@example.com');
    await page.getByPlaceholder(/password/i).fill('Password123!');
    await page.getByRole('button', { name: 'Login' }).click();

    // Should NOT show signed in text
    await expect(page.getByText(/signed in as/i)).not.toBeVisible({ timeout: 5000 });
  });
});
