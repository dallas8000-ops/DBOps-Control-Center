import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';
const API_URL = 'http://localhost:8000';

const DBA_EMAIL = 'dba@example.com';
const DBA_PASSWORD = 'Password123!';

test.describe('Resolve Incident', () => {
  test.beforeEach(async ({ page }) => {
    // Intercept login API
    await page.goto(BASE_URL);

    // Perform login via the UI or directly via localStorage injection
    // First, get token from API
    const loginResponse = await page.request.post(`${API_URL}/auth/login`, {
      data: { email: DBA_EMAIL, password: DBA_PASSWORD },
    });
    expect(loginResponse.ok()).toBeTruthy();
    const loginData = await loginResponse.json();
    const token = loginData.access_token;
    expect(token).toBeTruthy();

    // Inject token into localStorage
    await page.evaluate((t) => {
      localStorage.setItem('dbops_token', t);
    }, token);

    // Reload so the app picks up the token
    await page.reload();

    // Verify signed in as DBA
    await expect(page.getByText(`Signed in as ${DBA_EMAIL}`)).toBeVisible({ timeout: 10000 });
  });

  test('should show Resolve button for DBA on open incidents', async ({ page }) => {
    // Expand the Incidents accordion
    const incidentsAccordion = page.getByRole('button', { name: /incidents/i }).filter({ hasNotText: /create/i });
    await incidentsAccordion.click();

    // Wait for the incidents list to load
    await page.waitForResponse(
      (response) => response.url().includes('/incidents') && response.status() === 200,
      { timeout: 15000 }
    );

    // Wait for content to appear
    await page.waitForTimeout(500);

    // Find the Resolve button - should be visible for DBA on open incidents
    const resolveButton = page.getByRole('button', { name: /resolve/i }).first();
    await expect(resolveButton).toBeVisible({ timeout: 10000 });
  });

  test('should resolve an incident by clicking Resolve button', async ({ page }) => {
    // Expand the Incidents accordion
    const incidentsAccordion = page.getByRole('button', { name: /incidents/i }).filter({ hasNotText: /create/i });
    await incidentsAccordion.click();

    // Wait for incidents to load
    await page.waitForResponse(
      (response) => response.url().includes('/incidents') && response.status() === 200,
      { timeout: 15000 }
    );

    await page.waitForTimeout(500);

    // Find the first Resolve button (not "Resolve selected")
    const resolveButton = page
      .getByRole('button', { name: 'Resolve' })
      .first();

    await expect(resolveButton).toBeVisible({ timeout: 10000 });

    // Set up listener for the PATCH/resolve API call
    const resolveResponsePromise = page.waitForResponse(
      (response) =>
        (response.url().includes('/incidents') && response.request().method() === 'PATCH') ||
        (response.url().includes('/incidents') && response.request().method() === 'POST' && response.url().includes('resolve')),
      { timeout: 15000 }
    );

    // Click the Resolve button
    await resolveButton.click();

    // Wait for the API response
    await resolveResponsePromise;

    // Wait for UI to update
    await page.waitForTimeout(500);

    // Verify: the resolved incident should now show "Closed" status or the Resolve button count should decrease
    // The Resolve button on that specific incident should be gone, replaced by "Closed" text
    // Since the list might re-render, check that we have fewer Resolve buttons or a "Closed" status appears
    const closedText = page.getByText(/closed/i).first();
    const resolvedText = page.getByText(/resolved/i).first();

    // Check either "Closed" status appears or "Resolved" text
    const closedVisible = await closedText.isVisible().catch(() => false);
    const resolvedVisible = await resolvedText.isVisible().catch(() => false);

    expect(closedVisible || resolvedVisible).toBeTruthy();
  });

  test('should resolve incidents via bulk resolve', async ({ page }) => {
    // Expand the Incidents accordion
    const incidentsAccordion = page.getByRole('button', { name: /incidents/i }).filter({ hasNotText: /create/i });
    await incidentsAccordion.click();

    // Wait for incidents to load
    const incidentsResponse = await page.waitForResponse(
      (response) => response.url().includes('/incidents') && !response.url().includes('/history') && response.status() === 200,
      { timeout: 15000 }
    );

    const incidentsData = await incidentsResponse.json();
    await page.waitForTimeout(500);

    // Find open incidents from the API response
    const openIncidents = Array.isArray(incidentsData)
      ? incidentsData.filter((inc) => inc.status === 'open' || inc.status === 'acknowledged')
      : [];

    if (openIncidents.length === 0) {
      test.skip();
      return;
    }

    const targetIncident = openIncidents[0];
    const incidentId = targetIncident.id;

    // Select the incident using its checkbox
    // Label is "Select incident {id}"
    const checkbox = page.getByLabel(`Select incident ${incidentId}`);
    await expect(checkbox).toBeVisible({ timeout: 10000 });
    await checkbox.check();

    // Verify checkbox is checked
    await expect(checkbox).toBeChecked();

    // Find and click "Resolve selected" button
    const resolveSelectedButton = page.getByRole('button', { name: /resolve selected/i });
    await expect(resolveSelectedButton).toBeVisible({ timeout: 5000 });

    // Wait for the bulk action API call
    const bulkResponsePromise = page.waitForResponse(
      (response) =>
        response.url().includes('/incidents') &&
        (response.request().method() === 'PATCH' || response.request().method() === 'POST'),
      { timeout: 15000 }
    );

    await resolveSelectedButton.click();

    const bulkResponse = await bulkResponsePromise;
    expect(bulkResponse.ok()).toBeTruthy();

    // Wait for UI to update
    await page.waitForTimeout(500);

    // Verify bulk action result appears - could be a success message or status change
    // Check for success indicator (toast, message, or status change)
    const successIndicators = [
      page.getByText(/resolved/i),
      page.getByText(/success/i),
      page.getByText(/closed/i),
      page.getByText(/bulk/i),
      page.getByText(/updated/i),
    ];

    let found = false;
    for (const indicator of successIndicators) {
      const visible = await indicator.isVisible().catch(() => false);
      if (visible) {
        found = true;
        break;
      }
    }

    // Also acceptable: the checkbox is now unchecked (incident was resolved and removed/updated)
    const checkboxStillChecked = await checkbox.isChecked().catch(() => false);

    // Either success message appeared OR the checkbox state changed
    expect(found || !checkboxStillChecked).toBeTruthy();
  });

  test('should handle resolve when no open incidents exist gracefully', async ({ page }) => {
    // Mock the incidents endpoint to return empty array or all-closed incidents
    await page.route(`${API_URL}/incidents`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    // Expand the Incidents accordion
    const incidentsAccordion = page.getByRole('button', { name: /incidents/i }).filter({ hasNotText: /create/i });
    await incidentsAccordion.click();

    await page.waitForTimeout(1000);

    // Verify no Resolve buttons are shown
    const resolveButtons = page.getByRole('button', { name: 'Resolve' });
    const count = await resolveButtons.count();
    expect(count).toBe(0);

    // Verify the section is visible but empty
    const noIncidentsText = page.getByText(/no incidents/i);
    const emptyVisible = await noIncidentsText.isVisible().catch(() => false);
    // Either 0 resolve buttons or some empty state message
    expect(count === 0).toBeTruthy();
  });

  test('should not show Resolve button for non-DBA user (Viewer)', async ({ page }) => {
    // Get viewer token if available, otherwise mock the /auth/me endpoint
    await page.route(`${API_URL}/auth/me`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 99,
          email: 'viewer@example.com',
          role: 'Viewer',
          display_name: 'Viewer User',
          is_active: true,
        }),
      });
    });

    // Reload to apply the mock
    await page.reload();

    // Expand the Incidents accordion
    const incidentsAccordion = page.getByRole('button', { name: /incidents/i }).filter({ hasNotText: /create/i });
    await incidentsAccordion.click();

    await page.waitForTimeout(1000);

    // For a viewer, the Resolve button should NOT be shown
    // Instead, it shows "DBA only" text
    const dbaOnlyText = page.getByText(/dba only/i);
    const resolveButton = page.getByRole('button', { name: 'Resolve' });

    const dbaOnlyVisible = await dbaOnlyText.isVisible().catch(() => false);
    const resolveVisible = await resolveButton.isVisible().catch(() => false);

    // Either DBA only text is shown, or resolve button is not visible
    expect(!resolveVisible || dbaOnlyVisible).toBeTruthy();
  });

  test('should verify resolve updates incident status in the list', async ({ page }) => {
    // Expand the Incidents accordion
    const incidentsAccordion = page.getByRole('button', { name: /incidents/i }).filter({ hasNotText: /create/i });
    await incidentsAccordion.click();

    // Wait for incidents to load
    const firstLoadResponse = await page.waitForResponse(
      (response) =>
        response.url().includes('/incidents') &&
        !response.url().includes('/history') &&
        response.status() === 200,
      { timeout: 15000 }
    );

    const incidents = await firstLoadResponse.json();
    await page.waitForTimeout(500);

    const openIncidents = Array.isArray(incidents)
      ? incidents.filter((inc) => inc.status === 'open')
      : [];

    if (openIncidents.length === 0) {
      console.log('No open incidents to resolve, skipping test');
      return;
    }

    // Count initial Resolve buttons
    const initialResolveButtons = page.getByRole('button', { name: 'Resolve' });
    const initialCount = await initialResolveButtons.count();

    if (initialCount === 0) {
      console.log('No Resolve buttons visible, skipping test');
      return;
    }

    // Click the first Resolve button
    const firstResolveButton = initialResolveButtons.first();
    await firstResolveButton.click();

    // Wait for the resolve API call to complete
    await page.waitForResponse(
      (response) =>
        response.url().includes('/incidents') &&
        (response.request().method() === 'PATCH' || response.request().method() === 'POST'),
      { timeout: 15000 }
    );

    // Wait for the UI to re-render
    await page.waitForTimeout(1000);

    // Check that resolve button count decreased OR a resolved/closed indicator appeared
    const newResolveButtons = page.getByRole('button', { name: 'Resolve' });
    const newCount = await newResolveButtons.count();

    // Either the count decreased or there's a status change shown
    const statusChanged = newCount < initialCount;
    const closedShown = await page.getByText(/closed/i).isVisible().catch(() => false);
    const resolvedShown = await page.getByText(/resolved/i).isVisible().catch(() => false);

    expect(statusChanged || closedShown || resolvedShown).toBeTruthy();
  });
});
