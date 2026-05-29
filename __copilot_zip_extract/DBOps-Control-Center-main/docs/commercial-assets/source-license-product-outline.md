# Source license + product description (outline)

**Purpose:** Copy/paste starting structure for a storefront (Gumroad, Lemon Squeezy, etc.), landing page, or appendix to a quote. **Not legal advice**—have a qualified attorney review before high-value or enterprise sales, especially if you assign copyright or allow redistribution.

---

## Part A — Product description (marketing + checkout page)

Use  short sections buyers scan in order.

### 1) One-line pitch
- *Example:* “Full-stack internal ops dashboard: JWT/RBAC, incidents with audit history, whitelisted SQL reports, schedules, admin audit—FastAPI + React + Postgres, Docker + Render-ready.”

### 2) Who it’s for
- Small teams / consultancies building **internal** tooling  
- Developers who want a **working baseline** instead of greenfield  
- *Optional line:* “Not positioned as a regulated compliance product out of the box.”

### 3) What’s included (deliverables)
- Source access method (e.g. private repo invite, versioned ZIP, tagged release `v…`)  
- **README** + runbook pointers (local Docker Compose, Render env vars)  
- **Written tutorial** scope if sold separately (e.g. setup, first DBA, incidents, reports, troubleshooting)—page count or topic list  
- **Explicit exclusions** (e.g. no hosted SaaS from you, no SLA unless purchased, no custom feature work unless SOW)

### 4) Technical snapshot (honest)
- Stack list (backend, frontend, DB, migrations)  
- **Maturity note** (e.g. “~85% toward a hardened internal tool; see README for gaps: observability, multi-replica scheduler, SMTP email hook, SSO, etc.”)  
- **Support of deployment:** “Buyer deploys on their infrastructure; seller does not operate production unless separately contracted.”

### 5) License choice (buyer sees this upfront)
- State which variant applies: **Variant 1 — Internal use** or **Variant 2 — Consultant / client work** (see Part B).  
- Price, currency, updates policy (e.g. “updates for 90 days” / “single major version” / “as-is snapshot”).

### 6) Support boundaries
- Channels (email only, response-time aspirational, not a legal SLA unless contracted)  
- What’s out of scope (custom code, security review, penetration test, compliance certification)

### 7) Purchase flow
- Pay → accept terms → delivery (automated or manual within X business days)  
- Refund policy only if you intend one (many digital source sales are **no refunds** once delivered—say clearly if so, subject to local consumer rules).

### 8) Contact
- Email / form for pre-sales questions

---

## Part B — Source license (contract outline)

Use numbered clauses. Replace bracketed fields.

### Preamble
- **Parties:** Licensor `[legal name]`; Licensee `[name / company]`  
- **Effective date:** purchase / delivery date  
- **Software:** “DBOps Control Center” source code and documentation as delivered (define version or commit/tag)

### 1. Grant of license
- **Non-exclusive** (you can sell/license to others unless you negotiate exclusive)  
- **Purpose-limited grant** — pick one:
  - **Variant 1 — Internal use only:** Licensee may use, run, modify, and deploy the Software **solely for its own internal business operations**. No redistribution of source or binary to third parties except as needed for Licensee’s own hosting providers under confidentiality.
  - **Variant 2 — Consultant / agency:** Licensee may use, modify, and deploy the Software **for its own internal operations** and **for the benefit of up to `[N]` end clients** as part of delivered work product, provided Licensee does not **sell, sublicense, or publicly distribute** the Software as a standalone template or marketplace product. *(Tighten “N”, client definition, and non-compete language with counsel if needed.)*

### 2. Restrictions (typical)
- No **removal** of copyright/license notices from source (unless you allow)  
- No use in **illegal** activity; no misrepresentation of affiliation  
- **No resale / no public repo** of the purchased source as a product (unless you explicitly allow “white-label resale”—usually a different tier)  
- **No trademark** grant unless you give a written brand policy

### 3. Ownership
- Licensor retains all right, title, and interest **except** the license expressly granted  
- **No assignment** of copyright unless a separate written instrument says otherwise

### 4. Third-party components
- Software may include OSS under their respective licenses (point to `package` files / notices). Licensee must comply with those **in addition to** this agreement.

### 5. Updates
- Define: included updates for `[period]` / none / major version only / link to changelog

### 6. Fees
- One-time fee as paid via `[platform]`; taxes if applicable

### 7. Confidentiality (optional but useful for private source)
- Source and docs are **confidential**; no disclosure except to employees/contractors under need-to-know and equivalent obligations

### 8. Warranty disclaimer (typical pattern)
- **AS IS / AS AVAILABLE**; **no** express or implied warranties including **merchantability**, **fitness for a particular purpose**, **non-infringement**—to the maximum extent permitted by law  
- Buyer responsible for **security**, **backups**, **compliance**, and **fitness** for their environment

### 9. Limitation of liability (typical pattern—counsel jurisdiction-specific)
- Cap: **fees paid** or **greater of fees paid / $[X]**  
- Exclusion of **consequential**, **indirect**, **special**, **punitive** damages (as permitted by law)  
- Carveouts only if required (e.g. gross negligence, willful misconduct—jurisdiction-dependent)

### 10. Indemnification (optional; often asymmetrical—get advice)
- Many small sellers **omit** buyer→seller indemnity or keep it narrow. If included, define scope carefully.

### 11. Term and termination
- **Perpetual** license to the delivered version subject to restrictions, **or** subscription-style if you prefer  
- Termination for **material breach** + cure period  
- Obligations on termination (stop use, destroy copies—practical for source; clarify what “destroy” means for repos)

### 12. Export / sanctions (if relevant)
- Buyer warrants compliance with export and sanctions laws

### 13. Governing law / venue
- `[State/country]` and `[courts / arbitration]` — **pick with counsel**

### 14. Entire agreement / assignment / notices
- Standard boilerplate: entire agreement, amendments in writing, assignment by Licensor allowed, notices by email

### 15. Acceptance
- “By purchasing / clicking accept / paying invoice, Licensee agrees…”

---

## Part C — Checklist before you publish

- [ ] Pick **Variant 1 vs 2** (or define a third “enterprise” tier).  
- [ ] Confirm repo **does not** contain secrets (`.env`, keys); add `.env.example` only.  
- [ ] Decide **refund** and **chargeback** posture (platform rules + consumer law).  
- [ ] Decide **delivery** mechanism and **version pin**.  
- [ ] Optional: add `NOTICE` / third-party attribution file if not already complete.

---

## How to use this doc

1. Fill **Part A** for your storefront or PDF one-pager.  
2. Turn **Part B** into your actual **EULA / Source License Agreement** with an attorney for your jurisdiction and risk tolerance.  
3. Keep marketing claims aligned with **README** maturity so buyers aren’t surprised.
