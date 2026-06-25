# Demo video script — full product tour (5–8 minutes)

**Purpose:** Listing/sales video. Buyers of source code should **see it work** before reading docs. Record at **1920×1080**, browser zoom 100%, dark or system theme — match your live demo.

**Evaluation accounts:** use private workshop credentials or local `seed-demo` on your machine — not published on the public demo.

---

## 0:00–0:30 — Hook & product frame

**On screen:** Login page — header “Database Operations Platform”, footer “Proprietary software · Licensed deployment”.

**Say:**  
“This is DBOps Control Center — a deployable operations platform for PostgreSQL. Your team gets incidents, audited read-only reports, and role-based access without handing out SQL credentials. I’ll show the full loop in a few minutes.”

**Do:** Brief pause on health strip (API connected).

---

## 0:30–1:15 — Sign-in & RBAC context

**Do:** Log in as **Analyst**.

**Say:**  
“JWT authentication with three roles — Viewer, Analyst, DBA — enforced on every API route, not just the UI.”

**On screen:** Top bar “Signed in as … (Analyst)”, operational summary accordion.

---

## 1:15–2:15 — Incidents (create, triage, comment)

**Do:** Expand **Create Incident** → create medium-severity incident with owner and optional due date.

**Do:** Expand **Incidents** → filter/sort → open **History** → add a short **comment** (handoff note).

**Say:**  
“Analysts create and edit incidents; every change and comment lands in an audit history you can export to CSV.”

**Do:** Log out → log in as **DBA** → bulk-select incident → **Acknowledge** or **Resolve** (show quick actions bar).

**Say:**  
“DBAs get bulk resolve and full resolution workflow; failed bulk actions roll back with a clear message.”

---

## 2:15–3:15 — Whitelisted SQL reports

**Do:** Expand **SQL Reports** → select catalog report → **Run report** → show results table.

**Do:** **Export CSV**.

**Say:**  
“Reports are whitelisted and parameterized in code — no arbitrary SQL from the browser. Executions are logged for DBAs.”

---

## 3:15–4:00 — AI assist (optional but differentiating)

**Do:** Expand **AI Operations Assist** → enter plain-English request → **Find report** → **Use this report** → show notice on reports panel.

**Do:** Enter incident ID → **Summarize incident** → show three-line handoff.

**Say:**  
“AI routes to existing reports only — it doesn’t generate SQL. Without an API key, heuristic mode still works for demos.”

---

## 4:00–4:45 — DBA: users, schedules, audit

**Do:** Stay as DBA. Scroll to **Business Metrics** (if visible) or **Create user** panel → mention user create / reset / disable (pick one quick action).

**Do:** Expand **Scheduled Reports** → show schedule form (daily/weekly, email or webhook) → mention existing schedule toggle.

**Do:** Expand **Report Audit Trail** → change view limit → **Refresh**.

**Say:**  
“DBAs govern users, schedules, and report execution history — the control plane buyers need for production.”

---

## 4:45–5:15 — Scheduler health & billing (optional env)

**Do:** Expand **Scheduler Health** → point at last iteration / processed count.

**Say:**  
“On PostgreSQL, advisory locking prevents duplicate schedule runs across API replicas.”

**Optional (if Stripe env configured):** Mention billing settings / checkout — otherwise say billing hooks are included in source with Stripe webhook paths.

---

## 5:15–5:45 — Viewer role (30 seconds)

**Do:** Log in as **Viewer** → show read-only: reports yes, create incident no, no bulk controls.

**Say:**  
“Viewers can run approved reports and see incidents — they cannot change operational data.”

---

## 5:45–6:30 — Deployment & what you’re buying

**On screen:** Switch to slide or browser tab: `render.yaml`, GitHub Actions green CI, or README “What’s included”.

**Say:**  
“You’re buying source: FastAPI, React, migrations, Docker Compose, Render blueprint, and CI with 69 backend and 21 frontend tests. Deploy on your infrastructure. Five known gaps remain — observability stack, attachments, external scheduler worker, distributed rate limits, and deep E2E edge tests — documented on one page so there are no surprises.”

**Close:**  
“Live demo link in the listing. Questions and licensing: email on the pitch doc. Thanks for watching.”

---

## Recording checklist

- [ ] Reset demo data: `python -m app reset-demo --yes` then `seed-demo` (or fresh DB)
- [ ] API + web URLs match listing (HTTPS on Render)
- [ ] No real customer data, secrets, or production keys in frame
- [ ] Cursor moves deliberately; pause 2s on audit tables after actions
- [ ] Export 1080p MP4; upload unlisted YouTube/Vimeo or attach to marketplace listing

**Related:** [demo-video-scripts.md](./demo-video-scripts.md) (shorter DBA-only and incident-only cuts).
