# DBOps Control Center - Stakeholder Enablement Workshop

## Workshop Overview

**Duration:** 2 hours
**Audience:** Operations teams, DBAs, engineering leads, business stakeholders
**Prerequisites:** 
- DBOps Control Center deployed in staging/production environment
- Participants have basic computer literacy
- No SQL knowledge required

**Learning Objectives:**
By the end of this workshop, participants will be able to:
- Navigate the DBOps Control Center dashboard
- Create and manage incidents
- Run and schedule reports
- Understand RBAC roles and permissions
- Review audit trails and activity logs
- Perform basic user administration (DBAs only)

---

## Workshop Agenda

### Part 1: Introduction and Overview (15 minutes)
- Welcome and objectives
- Problem statement: Why DBOps Control Center?
- Architecture overview
- Security and access control
- Demo: Live system tour

### Part 2: Incident Management (30 minutes)
- Creating incidents
- Editing and resolving incidents
- Filtering and searching incidents
- Incident history and audit trail
- Hands-on exercise

### Part 3: Reporting (30 minutes)
- Running whitelisted reports
- Understanding report parameters
- CSV export functionality
- Scheduling automated reports
- Hands-on exercise

### Part 4: User Administration (DBAs only) (20 minutes)
- Creating users
- Managing user roles
- Resetting passwords
- Enabling/disabling accounts
- Reviewing audit logs

### Part 5: Advanced Features (15 minutes)
- SSO/OIDC integration (if configured)
- AI assist features (if configured)
- Billing overview (if applicable)
- Q&A

### Part 6: Wrap-up (10 minutes)
- Summary and next steps
- Support resources
- Feedback session

---

## Part 1: Introduction and Overview

### 1.1 Welcome and Objectives (5 minutes)

**Facilitator Notes:**
- Introduce yourself and your role
- Have participants introduce themselves (name, role, experience level)
- State workshop objectives clearly
- Mention that no SQL knowledge is required

**Key Talking Points:**
- "DBOps Control Center gives your team safe database visibility without SQL access"
- "Every action is logged and auditable"
- "Three roles: Viewer (read-only), Analyst (create/edit), DBA (full admin)"

### 1.2 Problem Statement (5 minutes)

**The Challenge:**
- Database has the answers, but only a few people know SQL
- Raw database access is too dangerous to hand out
- Teams wait on developers to run queries
- No audit trail of who accessed what data

**The Solution:**
- Whitelisted SQL reports defined by DBAs
- Role-based access control enforced everywhere
- Full audit trail of all actions
- Scheduled reports with email delivery

### 1.3 Architecture Overview (3 minutes)

**High-Level Architecture:**
```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTPS
┌──────▼──────┐
│  Frontend   │ (React + Vite)
└──────┬──────┘
       │ API calls
┌──────▼──────┐
│   Backend   │ (FastAPI + PostgreSQL)
└──────┬──────┘
       │ SQL
┌──────▼──────┐
│  Database   │ (PostgreSQL)
└─────────────┘
```

**Key Components:**
- **Frontend:** React dashboard for user interaction
- **Backend:** FastAPI API with JWT authentication
- **Database:** PostgreSQL with Alembic migrations
- **Security:** JWT tokens, RBAC, rate limiting

### 1.4 Security and Access Control (2 minutes)

**Three-Tier RBAC:**
- **Viewer:** View incidents, run reports, view audit logs
- **Analyst:** Create/edit incidents, run reports, view audit logs
- **DBA:** Full access + user management, scheduled reports, billing

**Security Features:**
- JWT authentication with bcrypt password hashing
- Rate limiting on all endpoints
- Audit trail for all admin actions
- Optional SSO/OIDC integration

### 1.5 Demo: Live System Tour (5 minutes)

**Live Demo Script:**
1. Show login screen
2. Log in as DBA user
3. Navigate to dashboard overview
4. Show incident list
5. Show report catalog
6. Show admin overview (DBA only)
7. Log out

**Key Points to Highlight:**
- Clean, intuitive interface
- No SQL anywhere in the UI
- Clear role-based permissions
- Audit trail visible throughout

---

## Part 2: Incident Management

### 2.1 Creating Incidents (10 minutes)

**Concept:**
Incidents track operational issues, outages, or events that need team attention.

**Demo Steps:**
1. Click "Create Incident" button
2. Fill in required fields:
   - Title: "Database slow response times"
   - Severity: High
   - Owner: Select from dropdown
   - Description: "Users reporting 5+ second query times"
3. Set optional due date
4. Click "Create"
5. Show incident appears in list

**Hands-On Exercise (5 minutes):**
- Participants create their own test incident
- Use different severity levels
- Set due dates
- Review in incident list

**Key Teaching Points:**
- Severity levels: Low, Medium, High
- Status workflow: Open → Resolved
- Due dates help with prioritization
- Owner assignment for accountability

### 2.2 Editing and Resolving Incidents (10 minutes)

**Demo Steps:**
1. Click on an existing incident
2. Edit fields (title, severity, owner, due date)
3. Save changes
4. Show "Resolve" button (DBA only)
5. Resolve the incident
6. Show status change in list

**Hands-On Exercise (5 minutes):**
- Participants edit their incident
- Change severity or owner
- DBAs resolve their incident
- View resolved incidents

**Key Teaching Points:**
- All changes are logged in audit trail
- Only DBAs can resolve incidents
- Resolved incidents show in history
- Before/after diffs tracked

### 2.3 Filtering and Searching Incidents (5 minutes)

**Demo Steps:**
1. Show filter options:
   - Status: Open/Resolved
   - Severity: Low/Medium/High
   - Owner: Select specific owner
   - Search: Text search in title/description
   - Date range: Start/end dates
   - Overdue: Show only overdue items
2. Apply filters
3. Show sorted results (newest/oldest/severity)

**Hands-On Exercise (2 minutes):**
- Participants filter by severity
- Search for specific text
- Filter by owner
- Sort by different criteria

**Key Teaching Points:**
- Filters can be combined
- "Overdue" filter shows past-due open items
- Sort options help prioritize
- Clear filters resets to default view

### 2.4 Incident History and Audit Trail (5 minutes)

**Demo Steps:**
1. Click on an incident
2. Show "History" section
3. View chronological events:
   - Created
   - Updated (with field changes)
   - Resolved
4. Click "History CSV" to download
5. Show CSV file with full audit trail

**Key Teaching Points:**
- Every action is logged
- Before/after values tracked
- CSV export for compliance
- History is immutable

---

## Part 3: Reporting

### 3.1 Running Whitelisted Reports (10 minutes)

**Concept:**
Reports are pre-defined SQL queries that DBAs have approved as safe to run.

**Demo Steps:**
1. Navigate to "Reports" section
2. Show report catalog with descriptions
3. Select "Incidents by status"
4. Click "Run Report"
5. Show results in table format
6. Show row count and execution time

**Hands-On Exercise (5 minutes):**
- Participants run different reports
- Try "Recent incidents" with max_rows parameter
- Run "Open high-severity incidents"
- View results

**Key Teaching Points:**
- Reports are role-gated (some DBA-only)
- Parameters are validated
- Row counts are capped
- No arbitrary SQL execution

### 3.2 Understanding Report Parameters (5 minutes)

**Demo Steps:**
1. Select "Recent incidents" report
2. Show max_rows parameter (default: 50, range: 1-500)
3. Change to 100 rows
4. Run report
5. Show increased result set

**Key Teaching Points:**
- Parameters have type validation
- Min/max limits enforced
- Default values provided
- Safe parameter binding (no SQL injection)

### 3.3 CSV Export Functionality (5 minutes)

**Demo Steps:**
1. Run any report
2. Click "Export CSV" button
3. Show CSV download
4. Open CSV file
5. Show headers and escaped values

**Hands-On Exercise (2 minutes):**
- Participants export report to CSV
- Open in Excel/Google Sheets
- Verify data integrity

**Key Teaching Points:**
- CSV includes headers
- Values properly escaped
- Same role permissions as report
- Useful for external analysis

### 3.4 Scheduling Automated Reports (10 minutes)

**Concept:**
Schedule reports to run automatically daily or weekly with email delivery.

**Demo Steps:**
1. Navigate to "Schedules" section (DBA only)
2. Click "Create Schedule"
3. Configure:
   - Report: "Incidents by status"
   - Cadence: Daily
   - Time: 09:00 UTC
   - Delivery: Email (if SMTP configured)
   - Email address: user@example.com
4. Enable schedule
5. Show schedule in list with next run time

**Hands-On Exercise (5 minutes):**
- DBAs create a test schedule
- Set different cadence (daily/weekly)
- Configure email delivery (if SMTP available)
- View schedule overview

**Key Teaching Points:**
- Schedules run automatically
- Failures are logged
- Email delivery optional (requires SMTP)
- DBAs can enable/disable schedules
- Next run time calculated automatically

---

## Part 4: User Administration (DBAs Only)

### 4.1 Creating Users (5 minutes)

**Demo Steps:**
1. Navigate to "Users" section
2. Click "Create User"
3. Fill in:
   - Email: newuser@example.com
   - Role: Analyst
   - Password: (temporary password)
4. Click "Create"
5. Show user in list

**Hands-On Exercise (3 minutes):**
- DBAs create test users
- Assign different roles
- Verify users appear in list

**Key Teaching Points:**
- Email must be unique
- Role determines permissions
- Temporary password should be changed
- Self-protection (can't delete/disable self)

### 4.2 Managing User Roles (3 minutes)

**Demo Steps:**
1. Select existing user
2. Change role from Viewer to Analyst
3. Save changes
4. Show audit log entry

**Key Teaching Points:**
- Role changes are audited
- Changes take effect immediately
- No logout required for new permissions

### 4.3 Resetting Passwords (3 minutes)

**Demo Steps:**
1. Select user
2. Click "Reset Password"
3. Enter new temporary password
4. Save
5. User logs in with new password

**Key Teaching Points:**
- Only DBAs can reset passwords
- Passwords are bcrypt-hashed
- Users should change after first login
- Audit trail records reset

### 4.4 Enabling/Disabling Accounts (4 minutes)

**Demo Steps:**
1. Select user
2. Click "Disable Account"
3. Show user status changes
4. Try to log in as disabled user (show error)
5. Re-enable account

**Key Teaching Points:**
- Disabled users blocked immediately
- No access to any features
- Audit trail records enable/disable
- Useful for offboarding or security

### 4.5 Reviewing Audit Logs (5 minutes)

**Demo Steps:**
1. Navigate to "User Audit" section
2. Show audit log entries:
   - User created
   - Password reset
   - Role changed
   - Account disabled
3. Filter by action type
4. Show actor and timestamp

**Key Teaching Points:**
- Every admin action logged
- Actor identity tracked
- Timestamps for compliance
- Immutable audit trail

---

## Part 5: Advanced Features

### 5.1 SSO/OIDC Integration (5 minutes)

**If Configured:**
- Show "Sign in with SSO" button on login
- Demo OIDC flow (Google/Microsoft)
- Show auto-provisioned user creation
- Explain default role assignment

**Key Teaching Points:**
- No password management for SSO users
- Automatic user provisioning
- Configurable default role
- PKCE flow for security

### 5.2 AI Assist Features (5 minutes)

**If Configured:**
- Show "Find Report" AI helper
- Demo natural language to report routing
- Show "Summarize Incident" AI helper
- Demo incident handoff summary

**Key Teaching Points:**
- AI falls back to heuristics if no API key
- Only considers user-visible reports
- No SQL generation
- Safe, deterministic behavior

### 5.3 Billing Overview (5 minutes)

**If Applicable:**
- Show billing status in admin overview
- Explain Stripe integration
- Show subscription management
- Demo checkout flow (if test mode)

**Key Teaching Points:**
- Billing state tracked in database
- Stripe webhook updates status
- Plan limits enforced
- Audit trail for billing changes

---

## Part 6: Wrap-up

### 6.1 Summary and Next Steps (5 minutes)

**Workshop Summary:**
- Incident management: Create, edit, resolve, filter
- Reporting: Run reports, export CSV, schedule automation
- User administration: Create, manage roles, reset passwords
- Audit trails: Full visibility into all actions

**Next Steps for Participants:**
- Log in to production environment
- Create first incident
- Run a report
- Explore dashboard features
- Review documentation

**Next Steps for Organization:**
- Configure SSO/OIDC if needed
- Set up SMTP for email delivery
- Configure scheduled reports
- Set up monitoring and alerts
- Review security settings

### 6.2 Support Resources (3 minutes)

**Documentation:**
- README.md: Quick start and overview
- docs/OPERATIONAL_READINESS.md: Deployment and operations
- docs/INCIDENT_RESPONSE.md: Incident response procedures
- docs/MIGRATION_ROLLBACK.md: Database migration procedures

**Support Contacts:**
- Email: dallas8000@gmail.com
- GitHub Issues: https://github.com/dallas8000-ops/DBOps-Control-Center/issues
- Response time: < 24 hours for non-critical, < 4 hours for critical

**Community:**
- GitHub repository for updates
- Release notes in repository
- Feature requests via GitHub issues

### 6.3 Feedback Session (2 minutes)

**Feedback Questions:**
- What was most valuable?
- What was confusing?
- What features do you want to explore further?
- Any suggestions for improvement?

**Feedback Collection:**
- Written feedback form (optional)
- Open discussion
- Record action items

---

## Workshop Materials

### Pre-Workshop Checklist

**Facilitator:**
- [ ] Deploy DBOps Control Center to staging environment
- [ ] Create test users (DBA, Analyst, Viewer)
- [ ] Seed demo data (incidents, reports)
- [ ] Configure SMTP for email delivery (optional)
- [ ] Configure SSO/OIDC (optional)
- [ ] Test all features end-to-end
- [ ] Prepare demo scenarios
- [ ] Print handouts (optional)

**Participants:**
- [ ] Receive workshop invitation
- [ ] Review pre-workshop materials (optional)
- [ ] Bring laptop for hands-on exercises
- [ ] Have login credentials ready

### Handout Materials

**Quick Reference Card:**
```
DBOps Control Center - Quick Reference

Login: https://your-app.example.com
Support: dallas8000@gmail.com

Key Features:
- Incidents: Create, edit, resolve, filter
- Reports: Run, export CSV, schedule
- Users: Manage roles, reset passwords (DBA)
- Audit: View all activity logs

Common Tasks:
1. Create incident: Click "Create Incident"
2. Run report: Select report → Click "Run"
3. Export CSV: Click "Export CSV" on results
4. Schedule report: Schedules → "Create Schedule"
5. Reset password: Users → Select user → "Reset Password"
```

**Role Permissions Cheat Sheet:**
```
Viewer:
- View incidents
- Run reports (filtered catalog)
- View audit logs

Analyst:
- Everything in Viewer +
- Create/edit incidents
- Run all reports

DBA:
- Everything in Analyst +
- Resolve incidents
- User management
- Scheduled reports
- Billing settings
```

### Post-Workshop Follow-up

**Immediate Follow-up (1 week):**
- Send workshop summary email
- Share recorded demo (if available)
- Collect feedback
- Address outstanding questions

**Medium-term Follow-up (1 month):**
- Check usage metrics
- Identify training gaps
- Schedule advanced training if needed
- Gather feature requests

**Long-term Follow-up (3 months):**
- Review adoption rates
- Assess ROI
- Plan feature enhancements
- Consider additional training

---

## Troubleshooting Common Workshop Issues

**Login Failures:**
- Verify credentials are correct
- Check if account is disabled
- Ensure user has correct role
- Try password reset

**Reports Not Running:**
- Verify user has permission for report
- Check database connection
- Review error messages
- Contact support if persistent

**Schedules Not Executing:**
- Check scheduler health endpoint
- Verify schedule is enabled
- Review schedule configuration
- Check for errors in logs

**Slow Performance:**
- Check database connection
- Review query result sizes
- Consider adding indexes
- Contact support for optimization

---

## Customization Notes

**For Technical Teams:**
- Add deeper technical content
- Show API documentation
- Demo integration patterns
- Discuss security architecture

**For Business Teams:**
- Focus on business value
- Emphasize audit compliance
- Show reporting capabilities
- Discuss cost savings

**For DBAs:**
- Deep dive into report catalog
- Show SQL query patterns
- Discuss database optimization
- Cover migration procedures

---

## Facilitator Notes

**Tips for Success:**
- Keep demos simple and focused
- Allow time for hands-on practice
- Encourage questions throughout
- Adapt to audience skill level
- Have backup demo scenarios ready
- Test everything before workshop

**Common Pitfalls to Avoid:**
- Don't assume SQL knowledge
- Don't skip security discussion
- Don't rush through demos
- Don't ignore questions
- Don't use production data for demos
- Don't forget to mention audit trails

**Time Management:**
- Watch the clock closely
- Be prepared to skip sections if running late
- Prioritize hands-on exercises
- Keep Q&A focused
- End on time with clear next steps
