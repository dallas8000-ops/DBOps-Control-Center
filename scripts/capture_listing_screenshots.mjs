/**
 * Capture buyer-facing screenshots from the live Render demo (or local).
 * Usage: node scripts/capture_listing_screenshots.mjs
 * Output: docs/commercial-assets/listing-screenshots/*.png
 */
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, "..", "docs", "commercial-assets", "listing-screenshots");

const BASE_URL = process.env.SCREENSHOT_BASE_URL || "http://localhost:5173";
const DBA_EMAIL = process.env.SCREENSHOT_DBA_EMAIL;
const DBA_PASSWORD = process.env.SCREENSHOT_DBA_PASSWORD;

if (!DBA_EMAIL || !DBA_PASSWORD) {
  console.error("Set SCREENSHOT_DBA_EMAIL and SCREENSHOT_DBA_PASSWORD (never commit demo passwords).");
  process.exit(1);
}

async function waitForSignedIn(page) {
  await page.getByText(/Signed in as/i).waitFor({ timeout: 120_000 });
}

async function expandSection(page, title) {
  const toggle = page.getByRole("button", { name: title, exact: true });
  if ((await toggle.getAttribute("aria-expanded")) !== "true") {
    await toggle.click();
  }
  await page.waitForTimeout(400);
}

async function shot(page, name, fullPage = true) {
  const file = path.join(OUT_DIR, name);
  await page.screenshot({ path: file, fullPage });
  console.log(`Saved ${name}`);
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  console.log(`Opening ${BASE_URL} …`);
  await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 120_000 });
  await page.waitForTimeout(2000);
  await shot(page, "01-login-page.png");

  await page.getByRole("textbox", { name: "Email", exact: true }).fill(DBA_EMAIL);
  await page.getByPlaceholder("Password", { exact: true }).fill(DBA_PASSWORD);
  await page.getByRole("button", { name: "Login" }).click();
  await waitForSignedIn(page);
  await page.waitForTimeout(1500);
  await shot(page, "02-dba-dashboard-signed-in.png");

  await expandSection(page, "Operational Summary");
  await shot(page, "03-operational-summary.png");

  await expandSection(page, "Incidents");
  await shot(page, "04-incidents-list.png");

  await expandSection(page, "SQL Reports");
  await page.getByRole("button", { name: "Run report" }).click();
  await page.waitForTimeout(2000);
  await shot(page, "05-sql-reports-results.png");

  await expandSection(page, "AI Operations Assist");
  await shot(page, "06-ai-operations-assist.png");

  await expandSection(page, "Scheduled Reports (DBA)");
  await shot(page, "07-scheduled-reports-dba.png");

  await expandSection(page, "Report Audit Trail (DBA)");
  await shot(page, "08-report-audit-trail-dba.png");

  await expandSection(page, "Scheduler Health (DBA)");
  await shot(page, "09-scheduler-health-dba.png");

  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(300);
  await shot(page, "10-dba-full-dashboard.png");

  await browser.close();
  console.log(`\nDone. Screenshots in:\n${OUT_DIR}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
