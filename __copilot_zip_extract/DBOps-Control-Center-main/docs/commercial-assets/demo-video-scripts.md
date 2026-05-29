# Demo Video Scripts

## Script 1 - DBA Workflow (5-7 minutes)

### Goal
Show an operator how a DBA manages users, audit history, and scheduled reports safely.

### Scene Plan
1. Intro (30 sec)
- State problem: safe ops visibility without broad SQL access.
- Show dashboard landing page.

2. Authentication and Role Context (45 sec)
- Log in as DBA.
- Point out signed-in role indicator.

3. User Lifecycle Management (2 min)
- Create Analyst account.
- Reset password.
- Disable and re-enable account.
- Show user admin audit trail entry updates.

4. Report Governance (1.5 min)
- Open report catalog and run whitelisted report.
- Export CSV.
- Show report audit trail entries.

5. Scheduled Reports (1 min)
- Create daily schedule.
- Configure delivery target.
- Toggle schedule enabled/disabled.

6. Wrap (30 sec)
- Reinforce auditability and role boundaries.
- Call out deployment readiness.

## Script 2 - Incident-to-Report Workflow (5-7 minutes)

### Goal
Show how the team moves from operational incident intake to data-driven follow-up.

### Scene Plan
1. Intro (30 sec)
- State objective: shorten time from incident detection to reporting evidence.

2. Incident Intake (1.5 min)
- Log in as Analyst.
- Create incident with severity and owner.
- Update incident details.

3. Triage and Resolution (1.5 min)
- Show filtered incident view.
- Switch to DBA and resolve incident.

4. Reporting Evidence (2 min)
- Run recent incidents report.
- Show summary metrics update.
- Export CSV for stakeholder communication.

5. Scheduled Follow-up (1 min)
- As DBA, show schedule that sends recurring report delivery.
- Explain failure logging and remediation path.

6. Wrap (30 sec)
- Summarize operational loop: detect, triage, resolve, report, automate.
