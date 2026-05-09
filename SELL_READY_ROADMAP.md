# DBOps Control Center - Sell-Ready Roadmap (30 Days)

Goal: increase pricing power from medium to high by reducing technical risk, proving reliability, and improving buyer confidence.

## Success Metrics (End of 30 Days)

- Automated quality gates running on every push and PR.
- Backend and frontend smoke coverage for critical user journeys.
- Security hardening in place for auth-sensitive workflows.
- Reporting value features available for operational teams.
- Sales-ready collateral package complete.

---

## Week 1 - Tests + CI Foundation

### Epic 1: Backend integration coverage expansion

Deliverables:
- Add tests for auth flow edge cases (invalid credentials, disabled users, expired token behavior).
- Add tests for incident operations (create, edit, resolve, filter, sort).
- Add tests for report access control by role.

Acceptance criteria:
- At least 15 backend integration tests covering critical RBAC and incident/report workflows.
- Tests run in local command line with one command.
- All tests pass in CI.

Definition of done:
- Test failures block merge.
- README includes test command and scope.

### Epic 2: Frontend smoke tests

Deliverables:
- Add smoke tests for login/logout flow.
- Add smoke tests for create and edit incident flow.
- Add smoke tests for running a report and viewing results.

Acceptance criteria:
- At least 5 smoke tests for top user journeys.
- Tests run headless in CI.
- Failing smoke tests fail the pipeline.

Definition of done:
- CI includes frontend test stage.

### Epic 3: CI fail gates

Deliverables:
- Add CI workflow with separate jobs for backend and frontend.
- Enforce lint/build/test gates.

Acceptance criteria:
- CI workflow triggers on push and pull_request.
- Backend tests required and passing.
- Frontend build required and passing.
- Lint checks required and passing.

Definition of done:
- Branch cannot be merged if any gate fails.

---

## Week 2 - Security and Ops Hardening

### Epic 4: Rate limiting

Deliverables:
- Add rate limiting middleware for auth endpoints.
- Add stricter limits for login and token endpoints.

Acceptance criteria:
- Excessive requests return a clear throttling response.
- Limits configurable by environment variables.
- Documented in README runbook section.

Definition of done:
- Basic abuse scenario is blocked in test environment.

### Epic 5: Session and token handling improvements

Deliverables:
- Standardize token expiry handling in frontend.
- Ensure 401 handling consistently clears session and redirects.
- Improve user-facing messages for expired/invalid token and disabled account.

Acceptance criteria:
- 401 from protected endpoints causes deterministic logout behavior.
- No stale-token loops in UI.
- Frontend smoke tests cover expiry/unauthorized behavior.

Definition of done:
- All protected calls use shared unauthorized handler.

### Epic 6: Admin action audit trail

Deliverables:
- Add audit table + migration for admin user lifecycle actions.
- Log create, reset password, enable/disable, delete actions with actor and timestamp.
- Add DBA endpoint/UI table for viewing admin audit history.

Acceptance criteria:
- Every admin action creates exactly one audit row.
- Audit entries include actor_id, target_user_id/email snapshot, action, timestamp.
- DBA can view latest 100 entries in UI.

Definition of done:
- Migration applied cleanly in local and CI.

---

## Week 3 - Reporting Value Features

### Epic 7: CSV export

Deliverables:
- Add CSV export capability for report result sets.
- Add export button in report results UI.

Acceptance criteria:
- Export includes headers and escaped values.
- Export works for at least 3 report types.
- Frontend and backend tests cover CSV format and download action.

Definition of done:
- Export is role-gated same as report access.

### Epic 8: Better filtering and history

Deliverables:
- Expand incident and report history filters (date range, actor/user, status, severity).
- Improve empty-state and filter reset UX.

Acceptance criteria:
- Filter combinations return consistent results.
- Clear-filters action restores default list state.
- No UI errors when result set is empty.

Definition of done:
- Filtering behavior covered by tests.

---

## Week 4 - Scheduled Reports MVP + Commercial Assets

### Epic 9: Scheduled report runs (MVP)

Deliverables:
- Add schedule model and migration.
- Add API to create/list/enable/disable schedules.
- Add basic scheduler loop (daily/weekly) and execution logging.

Acceptance criteria:
- At least one scheduled report executes automatically and logs result.
- DBA can enable/disable schedule.
- Failures are logged with reason.

Definition of done:
- Scheduling documented with clear known limitations.

### Epic 10: Commercial assets package

Deliverables:
- 1-page pricing sheet (3 tiers).
- Onboarding checklist (day 0 to day 7).
- Support SLA document with response-time matrix.
- 2 demo video scripts (DBA workflow and incident-to-report workflow).

Acceptance criteria:
- Assets are saved in repo docs folder.
- Pricing tiers include scope boundaries and exclusions.
- SLA defines support channels, hours, severity levels, and targets.

Definition of done:
- All assets can be shared with prospects immediately.

---

## Suggested Pricing Targets After Completion

- Implementation package: USD 8,000 to 20,000.
- Monthly support: USD 800 to 2,500.
- Annual hosted equivalent: USD 6,000 to 24,000 per customer (team-size and support-tier dependent).

---

## Execution Checklist (Owner View)

- [ ] Week 1 complete and green in CI.
- [ ] Week 2 security and audit trail complete.
- [ ] Week 3 reporting value upgrades complete.
- [ ] Week 4 scheduling MVP complete.
- [ ] Commercial assets package complete and reviewed.

If all five are checked, the product is positioned for medium-to-high price discussions with materially lower buyer risk.
