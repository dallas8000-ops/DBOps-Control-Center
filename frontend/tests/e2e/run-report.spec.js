import { test, expect } from '@playwright/test';

const BASE_URL = process.env.VITE_API_URL || 'http://localhost:8000';
const APP_URL = 'http://localhost:5173';

test.describe('Run Report', () => {
  test.beforeEach(async ({ page }) => {
    // Intercept login API
    await page.route('**/auth/login', async (route) => {
      const request = route.request();
      if (request.method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            access_token: 'test-dba-token',
            token_type: 'bearer',
          }),
        });
      } else {
        await route.continue();
      }
    });

    // Intercept /auth/me
    await page.route('**/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          email: 'dba@example.com',
          role: 'DBA',
          display_name: 'DBA User',
          is_active: true,
        }),
      });
    });

    // Intercept incidents list
    await page.route('**/incidents', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        });
      } else {
        await route.continue();
      }
    });

    // Intercept reports/run
    await page.route('**/reports/run', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          report_key: 'incidents_by_status',
          columns: ['status', 'total'],
          rows: [
            ['open', 5],
            ['resolved', 12],
            ['acknowledged', 3],
          ],
          row_count: 3,
          truncated: false,
          duration_ms: 42,
        }),
      });
    });

    // Intercept reports/schedules
    await page.route('**/reports/schedules', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        });
      } else {
        await route.continue();
      }
    });

    // Intercept reports/export/csv
    await page.route('**/reports/export/csv', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/csv',
        body: 'status,total\nopen,5\nresolved,12\nacknowledged,3\n',
      });
    });

    // Navigate to the app
    await page.goto(APP_URL);

    // Perform login
    await page.fill('input[type="email"], input[placeholder*="email" i], input[name="email"]', 'dba@example.com');
    await page.fill('input[type="password"], input[placeholder*="password" i], input[name="password"]', 'Password123!');
    await page.click('button[type="submit"], button:has-text("Sign in"), button:has-text("Login")');

    // Wait for successful login
    await expect(page.locator('text=dba@example.com').or(page.locator('text=Signed in as')).or(page.locator('text=DBA'))).toBeVisible({ timeout: 10000 });
  });

  test('should expand SQL Reports section and show heading', async ({ page }) => {
    // Find and click the SQL Reports accordion button
    const sqlReportsButton = page.getByRole('button', { name: /SQL Reports/i });
    await expect(sqlReportsButton).toBeVisible({ timeout: 10000 });

    const isExpanded = await sqlReportsButton.getAttribute('aria-expanded');
    if (isExpanded !== 'true') {
      await sqlReportsButton.click();
    }

    // Wait for the SQL Reports section to be visible
    await expect(page.locator('text=SQL reports (read-only)')).toBeVisible({ timeout: 10000 });
  });

  test('should run a report and display results with columns and rows', async ({ page }) => {
    // Expand the SQL Reports section
    const sqlReportsButton = page.getByRole('button', { name: /SQL Reports/i });
    await expect(sqlReportsButton).toBeVisible({ timeout: 10000 });

    const isExpanded = await sqlReportsButton.getAttribute('aria-expanded');
    if (isExpanded !== 'true') {
      await sqlReportsButton.click();
    }

    await expect(page.locator('text=SQL reports (read-only)')).toBeVisible({ timeout: 10000 });

    // Click the Run report button
    const runReportButton = page.getByRole('button', { name: /Run report/i });
    await expect(runReportButton).toBeVisible({ timeout: 10000 });
    await runReportButton.click();

    // Wait for results to appear - look for table or result container
    await page.waitForResponse((response) =>
      response.url().includes('/reports/run') && response.status() === 200
    );

    // Verify report results are shown
    // The table should appear with data
    await expect(
      page.locator('table, [role="table"], .report-results, .report-table, [data-testid="report-results"]')
        .or(page.locator('text=status').first())
    ).toBeVisible({ timeout: 10000 });
  });

  test('should display at least one row in the report results', async ({ page }) => {
    // Expand the SQL Reports section
    const sqlReportsButton = page.getByRole('button', { name: /SQL Reports/i });
    await expect(sqlReportsButton).toBeVisible({ timeout: 10000 });

    const isExpanded = await sqlReportsButton.getAttribute('aria-expanded');
    if (isExpanded !== 'true') {
      await sqlReportsButton.click();
    }

    await expect(page.locator('text=SQL reports (read-only)')).toBeVisible({ timeout: 10000 });

    // Click Run report
    const runReportButton = page.getByRole('button', { name: /Run report/i });
    await expect(runReportButton).toBeVisible({ timeout: 10000 });
    await runReportButton.click();

    // Wait for API response
    await page.waitForResponse((response) =>
      response.url().includes('/reports/run') && response.status() === 200
    );

    // Wait for results to render
    await page.waitForTimeout(500);

    // Check for rows in the table - look for tbody rows or data cells
    const rowLocators = [
      page.locator('tbody tr'),
      page.locator('table tr').nth(1), // Second row (first is header)
      page.locator('[role="row"]').nth(1),
      page.locator('text=open'),
      page.locator('text=resolved'),
    ];

    let rowFound = false;
    for (const locator of rowLocators) {
      try {
        const count = await locator.count();
        if (count > 0) {
          rowFound = true;
          break;
        }
      } catch {
        // continue checking
      }
    }

    expect(rowFound).toBe(true);
  });

  test('should show column headers "status" and "total" in report output', async ({ page }) => {
    // Expand the SQL Reports section
    const sqlReportsButton = page.getByRole('button', { name: /SQL Reports/i });
    await expect(sqlReportsButton).toBeVisible({ timeout: 10000 });

    const isExpanded = await sqlReportsButton.getAttribute('aria-expanded');
    if (isExpanded !== 'true') {
      await sqlReportsButton.click();
    }

    await expect(page.locator('text=SQL reports (read-only)')).toBeVisible({ timeout: 10000 });

    // Click Run report
    const runReportButton = page.getByRole('button', { name: /Run report/i });
    await expect(runReportButton).toBeVisible({ timeout: 10000 });
    await runReportButton.click();

    // Wait for API response
    await page.waitForResponse((response) =>
      response.url().includes('/reports/run') && response.status() === 200
    );

    // Wait for results to render
    await page.waitForTimeout(500);

    // Look for 'status' column header
    await expect(
      page.locator('th:has-text("status"), td:has-text("status"), [data-col="status"]')
        .or(page.locator('text=status').first())
    ).toBeVisible({ timeout: 10000 });

    // Look for 'total' column header
    await expect(
      page.locator('th:has-text("total"), td:has-text("total"), [data-col="total"]')
        .or(page.locator('text=total').first())
    ).toBeVisible({ timeout: 10000 });
  });

  test('should use AI report finder and show "Use this report" suggestion', async ({ page }) => {
    // Set up AI/find report mock if needed
    await page.route('**/reports/find**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          report_key: 'high_severity_open',
          description: 'High severity incidents that are still open',
          suggestion: 'incidents_by_severity',
        }),
      });
    });

    await page.route('**/reports/suggest**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          report_key: 'high_severity_open',
          description: 'High severity incidents that are still open',
        }),
      });
    });

    await page.route('**/reports/search**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            report_key: 'high_severity_open',
            description: 'High severity incidents that are still open',
          },
        ]),
      });
    });

    // Expand the SQL Reports section
    const sqlReportsButton = page.getByRole('button', { name: /SQL Reports/i });
    await expect(sqlReportsButton).toBeVisible({ timeout: 10000 });

    const isExpanded = await sqlReportsButton.getAttribute('aria-expanded');
    if (isExpanded !== 'true') {
      await sqlReportsButton.click();
    }

    await expect(page.locator('text=SQL reports (read-only)')).toBeVisible({ timeout: 10000 });

    // Find the AI report finder input
    const aiInput = page.getByPlaceholder('Example: Are there any high severity incidents still open right now?');
    await expect(aiInput).toBeVisible({ timeout: 10000 });

    // Type a query
    await aiInput.fill('Are there any high severity incidents still open right now?');

    // Click the Find report button
    const findReportButton = page.getByRole('button', { name: /Find report/i });
    await expect(findReportButton).toBeVisible({ timeout: 10000 });
    await findReportButton.click();

    // Wait for suggestion to appear
    await expect(
      page.getByRole('button', { name: /Use this report/i })
        .or(page.locator('text=Use this report'))
    ).toBeVisible({ timeout: 15000 });
  });

  test('full flow: login, expand SQL Reports, run report, verify data', async ({ page }) => {
    // Expand the SQL Reports section
    const sqlReportsButton = page.getByRole('button', { name: /SQL Reports/i });
    await expect(sqlReportsButton).toBeVisible({ timeout: 10000 });

    // Toggle open if needed
    const ariaExpanded = await sqlReportsButton.getAttribute('aria-expanded');
    if (ariaExpanded !== 'true') {
      await sqlReportsButton.click();
    }

    // Verify section heading
    await expect(page.locator('text=SQL reports (read-only)')).toBeVisible({ timeout: 10000 });

    // Click Run report
    const runReportButton = page.getByRole('button', { name: /Run report/i });
    await expect(runReportButton).toBeVisible({ timeout: 10000 });

    const [response] = await Promise.all([
      page.waitForResponse((resp) =>
        resp.url().includes('/reports/run') && resp.status() === 200
      ),
      runReportButton.click(),
    ]);

    // Verify the API response is correct
    const responseBody = await response.json();
    expect(responseBody.columns).toContain('status');
    expect(responseBody.columns).toContain('total');
    expect(responseBody.rows.length).toBeGreaterThan(0);
    expect(responseBody.row_count).toBeGreaterThan(0);

    // Wait for render
    await page.waitForTimeout(500);

    // Verify column headers rendered in the UI
    await expect(
      page.locator('text=status').first()
    ).toBeVisible({ timeout: 10000 });

    await expect(
      page.locator('text=total').first()
    ).toBeVisible({ timeout: 10000 });
  });
});
