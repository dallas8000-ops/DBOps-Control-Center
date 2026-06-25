# DBOps Control Center — Hands-on Walkthrough

Use this document to **learn the product by doing**. Work through the exercises in order the first time; later, use it as a checklist when training new teammates.

| Document | Best for |
|----------|----------|
| **This walkthrough** | Step-by-step practice, training workshops, self-paced learning |
| [OPERATIONS_GUIDE.md](./OPERATIONS_GUIDE.md) | Reference: how sign-in, sessions, roles, and exit work end-to-end |
| [DEMO_VIDEO_5-8MIN.md](./commercial-assets/DEMO_VIDEO_5-8MIN.md) | Script to record a sales demo video |

**Time:** about **60–90 minutes** for all three roles, or **25 minutes** for Analyst-only.

---

## Before you start

### What you need

- A modern browser (Chrome, Edge, Firefox, or Safari)
- The app URL opened in the **address bar** (not inside an email preview)
- For the public demo: https://dbops-api-production-5047.up.railway.app

### Demo accounts

Use credentials from your **private deployment guide** or workshop handout. The public Railway demo does **not** publish admin passwords — request evaluation access from your Gilliom contact.

On your **own** deployment with an empty database, use **First-time setup (bootstrap DBA)** instead of seed accounts (see [OPERATIONS_GUIDE — Authentication](./OPERATIONS_GUIDE.md#2-authentication--getting-in)).

### Tips while learning

- Expand one **accordion section** at a time so the page stays readable.
- Leave **Live updates on** in the top bar unless you are comparing before/after counts.
- If something fails, check the **system status** strip on the login page and [Troubleshooting](#troubleshooting) at the bottom.

---

## Part 1 — Enter the application (5 minutes)

### Step 1.1 — Open the site

1. Go to https://dbops-api-production-5047.up.railway.app (or your team’s URL).
2. Wait a few seconds on first visit after a deploy if the Railway service is starting.
3. If you see a marketing page, click **Sign In** (top right) or **Start Free Trial**.

**You should see:** A login panel titled **Sign in**, with a green or yellow **system status** line about the API and PostgreSQL.

### Step 1.2 — Sign in as Viewer (read-only tour first)

1. Use your **Viewer** workshop credentials (email + password from your private handout).
2. Click **Login**.

**You should see:**

- Top bar: `Signed in as viewer@example.com (Viewer)`
- Accordion sections for summary, reports, and incidents — **no** “Create user” or “Business Metrics” blocks

**Checkpoint:** You are in the operations console. The Viewer role is intentionally limited so you can explore safely.

---

## Part 2 — Viewer walkthrough (15 minutes)

Goal: understand what stakeholders can see without changing data.

### Exercise 2.1 — Read the operational summary

1. Expand the **summary / metrics** section at the top of the dashboard (wording may show incident totals).
2. Note the cards: total incidents, open, resolved, high severity.

**Learn:** This is a live snapshot from the database, not a static chart.

### Exercise 2.2 — Run a read-only report

1. Expand **SQL Reports** (or **Reports**).
2. Pick a report from the dropdown (for example one about incidents by status).
3. Leave default parameters unless the form asks for dates.
4. Click **Run report**.
5. When rows appear, click **Export CSV** and open the file in a spreadsheet app.

**You should see:** A table of results and a downloaded `.csv` file.

**Learn:** Reports are fixed, approved queries — users cannot type arbitrary SQL.

### Exercise 2.3 — Browse incidents (no editing)

1. Expand **Incidents**.
2. Try a **filter**: set status to `open`, or type part of a title in **search**.
3. Click **History** on one incident.
4. Read the timeline; optionally add a **comment** (Viewers may comment — verify in your build; README RBAC says yes for comments).

**You should see:** History entries with actor and timestamps. You should **not** see create/edit/save buttons for incidents as Viewer.

### Exercise 2.4 — Sign out

1. Click **Log out** (top right).

**You should see:** Login screen again. Your session refresh token was revoked on the server when both tokens were present.

---

## Part 3 — Analyst walkthrough (25 minutes)

Goal: day-to-day operator — incidents and reports, no admin.

### Step 3.1 — Sign in

1. Log in with your **Analyst** workshop credentials.

### Exercise 3.1 — Create an incident

1. Expand **Create Incident**.
2. Fill in:
   - **Title:** `Walkthrough test — replica lag`
   - **Description:** `Learning exercise; safe to delete later`
   - **Severity:** `medium`
   - **Owner:** your email or `oncall`
   - **Due date:** optional — pick tomorrow if the field exists
3. Submit the form.

**You should see:** The new incident in the list below (refresh happens automatically if live updates are on).

### Exercise 3.2 — Edit and comment

1. In **Incidents**, find your new incident.
2. Start **Edit** (inline) — change severity to `high` or update the description → **Save**.
3. Open **History** → add comment: `Analyst walkthrough — triage note`.

**Learn:** Edits and comments are audited; DBA can export history as CSV later.

### Exercise 3.3 — Bulk actions (no resolve)

1. Select one or more **open** incidents (checkboxes).
2. Use the bulk bar: try **Acknowledge** or **Assign** (if assign, enter an owner email).
3. Read the toast or result summary (updated vs skipped).

**You should see:** Assign without an owner should be rejected by the API (validation). Resolve should **not** appear for Analyst.

### Exercise 3.4 — AI assist (optional)

1. Expand **AI Operations Assist**.
2. Type: `show open incidents by status`
3. Click **Find report** → if a report is suggested, click **Use this report**.
4. Enter your walkthrough incident **ID** → **Summarize incident**.

**Learn:** AI only suggests catalog reports and summaries; it does not run free-form SQL.

### Exercise 3.5 — Sign out

Log out before the DBA section so you practice a clean session end.

---

## Part 4 — DBA walkthrough (30 minutes)

Goal: control plane — users, schedules, billing, audit.

### Step 4.1 — Sign in

1. Log in with your **DBA** workshop credentials (not published on the public demo).

### Exercise 4.1 — Business metrics and plan limits

1. Scroll to **Business Metrics (DBA)**.
2. Read: active users, open incidents, schedule counts, **plan** and **billing status**.
3. Note **User seats left** and **Schedule slots left** — these enforce limits when you create users or schedules.

**Learn:** Stripe subscription (if configured) updates these via webhooks after checkout.

### Exercise 4.2 — Create a teammate (optional on shared demo)

On a **shared demo**, skip creating users or use a clearly fake email. On **your** install:

1. Expand **Create user (DBA)**.
2. Create `trainee-viewer@yourcompany.com` as **Viewer** with a strong password.
3. Find the user in the table → try **Reset password** or **Disable** (do not disable your own DBA account).

**You should see:** User admin audit log entries after actions.

### Exercise 4.3 — Resolve an incident

1. In **Incidents**, select an open incident you created earlier.
2. Bulk **Resolve** or use per-row resolve.
3. Confirm status becomes resolved in the list and in **History**.

### Exercise 4.4 — Scheduled report

1. Expand **Scheduled Reports**.
2. Create a schedule:
   - Report: pick a simple catalog report
   - Cadence: **daily** or **weekly**
   - Time: UTC hour/minute as shown
   - Delivery: `none` for demo (or email if SMTP is configured on your deploy)
3. Save → ensure schedule appears as **enabled**.

**Learn:** The API scheduler runs due jobs in the background; execution appears under **Report audit trail**.

### Exercise 4.5 — Report audit trail

1. Expand **Report audit trail** (DBA-only section).
2. Change view limit (3 / 10 / 25 / all) → **Refresh**.
3. Find your manual report run from Part 2 or 3.

### Exercise 4.6 — Stripe checkout (optional)

Only if billing is configured (`GET /health/billing` returns ok on your API):

1. In **Business Metrics**, click **Subscribe with Stripe**.
2. Complete **test mode** checkout in Stripe’s hosted page.
3. Return to the app → confirm billing status shows **active** and Stripe IDs appear.

See [STRIPE_RAILWAY_SETUP.md](./STRIPE_RAILWAY_SETUP.md) if checkout fails.

### Exercise 4.7 — Final sign-out

1. Click **Log out**.

**You should see:** Login screen. Re-opening the app should require password again (refresh token revoked).

---

## Part 5 — Three-role comparison (review)

After completing Parts 2–4, you should be able to answer:

| Question | Viewer | Analyst | DBA |
|----------|--------|---------|-----|
| Run reports & export CSV? | Yes | Yes | Yes |
| Create / edit incidents? | No | Yes | Yes |
| Bulk resolve? | No | No | Yes |
| Create users & schedules? | No | No | Yes |
| Subscribe with Stripe? | No | No | Yes |

---

## Learning checklist

Copy this into your onboarding ticket or workshop notes:

- [ ] Opened app in a real browser; saw healthy API/DB status
- [ ] Completed Viewer: summary, report run, CSV export, incident browse
- [ ] Completed Analyst: create incident, edit, comment, bulk ack/assign
- [ ] Completed DBA: metrics, resolve, schedule, report audit
- [ ] Used **Log out** and confirmed re-login required
- [ ] Read [OPERATIONS_GUIDE.md](./OPERATIONS_GUIDE.md) for session refresh and billing flow

---

## Suggested practice schedule

| Day | Focus | Time |
|-----|--------|------|
| Day 1 | Parts 1–2 (Viewer) | 20 min |
| Day 2 | Part 3 (Analyst) | 25 min |
| Day 3 | Part 4 (DBA) | 30 min |
| Day 4 | Re-run Analyst + DBA without this doc | 20 min |
| Day 5 | Train a colleague using Part 2 only | 15 min |

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| Blank page (only title in tab) | Full browser, not email preview; wait 60s; hard refresh (Ctrl+F5) |
| Login fails | Confirm demo password; check caps lock; rate limit — wait 1 minute |
| “Bootstrap complete” on register | Database already has users — sign in, don’t bootstrap |
| Report fails | Read error under report panel; DBA checks API logs on Railway |
| No SSO button | OIDC not configured on this deploy — use email/password |
| Log out but still “signed in” | Clear site data for the domain; ensure you clicked **Log out** with active session |

---

## Next steps

- **Operators:** keep [OPERATIONS_GUIDE.md](./OPERATIONS_GUIDE.md) bookmarked for day-to-day reference.
- **Buyers / implementers:** [onboarding-checklist-day0-day7.md](./commercial-assets/onboarding-checklist-day0-day7.md) and [DEPLOYMENT.md](../DEPLOYMENT.md).
- **Sales / demo recording:** [DEMO_VIDEO_5-8MIN.md](./commercial-assets/DEMO_VIDEO_5-8MIN.md).

---

*DBOps Control Center — training walkthrough. Evaluation passwords are for demo hosts only; rotate credentials in production.*
