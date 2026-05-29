# Listing screenshots (buyer presentation)

PNG captures of the live product UI for marketplace listings, pitch decks, and buyer email.

## Generate / refresh

From repo root (requires Node 20+):

```bash
cd scripts
npm install playwright
npx playwright install chromium
node capture_listing_screenshots.mjs
```

Defaults target production demo: https://dbops-web.onrender.com (DBA seed login).

Override:

```bash
set SCREENSHOT_BASE_URL=http://localhost:5173
node capture_listing_screenshots.mjs
```

## Files (after capture)

| File | Content |
|------|---------|
| `01-login-page.png` | Sign-in + first-time setup |
| `02-dba-dashboard-signed-in.png` | DBA session header + dashboard |
| `03-operational-summary.png` | Summary metrics accordion |
| `04-incidents-list.png` | Incidents list + filters |
| `05-sql-reports-results.png` | Report run + results |
| `06-ai-operations-assist.png` | AI assist panel |
| `07-scheduled-reports-dba.png` | DBA schedule management |
| `08-report-audit-trail-dba.png` | Report execution audit |
| `09-scheduler-health-dba.png` | Scheduler health (DBA) |
| `10-dba-full-dashboard.png` | Full scroll capture |

**Proprietary.** For buyer evaluation only — do not redistribute without license.
