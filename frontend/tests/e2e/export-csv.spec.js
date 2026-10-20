import { test, expect } from "@playwright/test";

test.describe("Export CSV", () => {
  test.beforeEach(async ({ page }) => {
    // Intercept login API
    await page.route("**/auth/login", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: "test-dba-token",
          token_type: "bearer",
        }),
      });
    });

    // Intercept /auth/me
    await page.route("**/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 1,
          email: "dba@example.com",
          role: "DBA",
          display_name: "DBA User",
          is_active: true,
        }),
      });
    });

    // Intercept GET /incidents
    await page.route("**/incidents", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
      } else {
        await route.continue();
      }
    });

    // Intercept POST /reports/run
    await page.route("**/reports/run", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          report_key: "incident_summary",
          columns: ["id", "title", "status", "severity", "owner", "created_at"],
          rows: [
            [1, "DB Connection Error", "open", "high", "dba@example.com", "2024-01-15T10:00:00Z"],
            [2, "Slow Query Alert", "resolved", "medium", "analyst@example.com", "2024-01-14T08:30:00Z"],
          ],
          row_count: 2,
          truncated: false,
          duration_ms: 42,
        }),
      });
    });

    // Intercept POST /reports/export/csv
    await page.route("**/reports/export/csv", async (route) => {
      const csvContent =
        "id,title,status,severity,owner,created_at\r\n" +
        "1,DB Connection Error,open,high,dba@example.com,2024-01-15T10:00:00Z\r\n" +
        "2,Slow Query Alert,resolved,medium,analyst@example.com,2024-01-14T08:30:00Z\r\n";
      await route.fulfill({
        status: 200,
        contentType: "text/csv",
        body: csvContent,
      });
    });

    // Intercept GET /reports/schedules
    await page.route("**/reports/schedules", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
      } else {
        await route.continue();
      }
    });

    await page.goto("http://localhost:5173");

    // Fill in login form
    await page.getByPlaceholder(/email/i).fill("dba@example.com");
    await page.getByPlaceholder(/password/i).fill("Password123!");
    await page.getByRole("button", { name: /sign in|login/i }).click();

    // Wait for successful login
    await expect(page.getByText(/signed in as/i)).toBeVisible({ timeout: 10000 });
  });

  test("should export CSV after running a report", async ({ page }) => {
    // Find and expand the SQL Reports accordion section
    const sqlReportsButton = page.getByRole("button", { name: /sql reports/i });
    await expect(sqlReportsButton).toBeVisible({ timeout: 10000 });

    const isExpanded = await sqlReportsButton.getAttribute("aria-expanded");
    if (isExpanded !== "true") {
      await sqlReportsButton.click();
    }

    // Wait for the SQL Reports section to be visible
    await expect(page.getByText(/sql reports.*read-only/i)).toBeVisible({ timeout: 10000 });

    // Click "Run report" button
    const runReportButton = page.getByRole("button", { name: /run report/i });
    await expect(runReportButton).toBeVisible({ timeout: 10000 });
    await runReportButton.click();

    // Wait for the Export CSV button to become enabled
    const exportCsvButton = page.getByRole("button", { name: /export csv/i });
    await expect(exportCsvButton).toBeVisible({ timeout: 10000 });
    await expect(exportCsvButton).not.toBeDisabled({ timeout: 10000 });

    // Set up download listener and click Export CSV
    const downloadPromise = page.waitForEvent("download", { timeout: 15000 });
    await exportCsvButton.click();

    // Wait for download to be triggered
    const download = await downloadPromise;

    // Verify download was triggered
    expect(download).toBeTruthy();

    // Verify the suggested filename looks like a CSV file
    const suggestedFilename = download.suggestedFilename();
    expect(suggestedFilename).toMatch(/\.csv$/i);

    // Read the downloaded file content
    const downloadPath = await download.path();
    expect(downloadPath).toBeTruthy();

    const fs = await import("fs");
    const fileContent = fs.readFileSync(downloadPath, "utf-8");

    // Verify it contains CSV-formatted data
    expect(fileContent).toBeTruthy();
    expect(fileContent.length).toBeGreaterThan(0);

    // Verify the CSV has appropriate headers including "status"
    const lines = fileContent.split(/\r?\n/).filter((line) => line.trim() !== "");
    expect(lines.length).toBeGreaterThan(0);

    const headerLine = lines[0].toLowerCase();
    expect(headerLine).toContain("status");

    // Verify there is at least one data row
    expect(lines.length).toBeGreaterThan(1);
  });

  test("Export CSV button should be disabled before running report", async ({ page }) => {
    // Find and expand the SQL Reports accordion section
    const sqlReportsButton = page.getByRole("button", { name: /sql reports/i });
    await expect(sqlReportsButton).toBeVisible({ timeout: 10000 });

    const isExpanded = await sqlReportsButton.getAttribute("aria-expanded");
    if (isExpanded !== "true") {
      await sqlReportsButton.click();
    }

    // Wait for the SQL Reports section heading to be visible
    await expect(page.getByText(/sql reports.*read-only/i)).toBeVisible({ timeout: 10000 });

    // Verify Export CSV button is disabled before running a report
    const exportCsvButton = page.getByRole("button", { name: /export csv/i });
    await expect(exportCsvButton).toBeVisible({ timeout: 10000 });
    await expect(exportCsvButton).toBeDisabled();
  });

  test("should export CSV with correct column headers", async ({ page }) => {
    // Find and expand the SQL Reports accordion section
    const sqlReportsButton = page.getByRole("button", { name: /sql reports/i });
    await expect(sqlReportsButton).toBeVisible({ timeout: 10000 });

    const isExpanded = await sqlReportsButton.getAttribute("aria-expanded");
    if (isExpanded !== "true") {
      await sqlReportsButton.click();
    }

    await expect(page.getByText(/sql reports.*read-only/i)).toBeVisible({ timeout: 10000 });

    // Run the report first
    const runReportButton = page.getByRole("button", { name: /run report/i });
    await expect(runReportButton).toBeVisible({ timeout: 10000 });
    await runReportButton.click();

    // Wait for report data to appear (table or results)
    await expect(page.getByRole("button", { name: /export csv/i })).not.toBeDisabled({ timeout: 10000 });

    // Set up download listener
    const downloadPromise = page.waitForEvent("download", { timeout: 15000 });

    // Click Export CSV
    await page.getByRole("button", { name: /export csv/i }).click();

    const download = await downloadPromise;
    expect(download).toBeTruthy();

    // Read file and verify headers
    const downloadPath = await download.path();
    const fs = await import("fs");
    const fileContent = fs.readFileSync(downloadPath, "utf-8");

    const lines = fileContent.split(/\r?\n/).filter((line) => line.trim() !== "");
    expect(lines.length).toBeGreaterThan(1);

    const headers = lines[0].toLowerCase().split(",");
    expect(headers).toContain("status");

    // Verify data rows contain expected status values
    const dataRows = lines.slice(1);
    const hasOpenOrResolved = dataRows.some(
      (row) => row.toLowerCase().includes("open") || row.toLowerCase().includes("resolved")
    );
    expect(hasOpenOrResolved).toBe(true);
  });
});
