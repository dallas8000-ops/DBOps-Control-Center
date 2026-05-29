"""Predefined read-only SQL reports (whitelist). Only these queries may run via /reports/run."""

from typing import Any

# Each report: title, description, allowed roles, SQL (must be SELECT-only), param specs.
REPORTS: dict[str, dict[str, Any]] = {
    "incidents_by_status": {
        "title": "Incidents by status",
        "description": "Count of incidents grouped by workflow status.",
        "roles": ("DBA", "Analyst", "Viewer"),
        "sql": """
            SELECT status, COUNT(*) AS incident_count
            FROM incidents
            GROUP BY status
            ORDER BY status
        """,
        "params": [],
    },
    "incidents_recent": {
        "title": "Recent incidents",
        "description": "Latest incidents ordered by created_at (bounded limit).",
        "roles": ("DBA", "Analyst", "Viewer"),
        "sql": """
            SELECT id, title, status, severity, owner, created_at
            FROM incidents
            ORDER BY created_at DESC
            LIMIT :max_rows
        """,
        "params": [
            {"name": "max_rows", "type": "int", "default": 50, "min": 1, "max": 500},
        ],
    },
    "open_high_severity": {
        "title": "Open high-severity incidents",
        "description": "Operational triage list for open + high severity items.",
        "roles": ("DBA", "Analyst"),
        "sql": """
            SELECT id, title, owner, created_at
            FROM incidents
            WHERE status = 'open' AND severity = 'high'
            ORDER BY created_at DESC
        """,
        "params": [],
    },
    "incidents_open_by_owner": {
        "title": "Open incidents by owner",
        "description": "Count of open incidents grouped by owner (triage ownership).",
        "roles": ("DBA", "Analyst", "Viewer"),
        "sql": """
            SELECT owner, COUNT(*) AS open_count
            FROM incidents
            WHERE status = 'open'
            GROUP BY owner
            ORDER BY open_count DESC, owner ASC
        """,
        "params": [],
    },
    "incidents_by_severity": {
        "title": "Incidents by severity",
        "description": "Volume of incidents grouped by severity (all statuses).",
        "roles": ("DBA", "Analyst", "Viewer"),
        "sql": """
            SELECT severity, COUNT(*) AS incident_count
            FROM incidents
            GROUP BY severity
            ORDER BY CASE severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 9 END
        """,
        "params": [],
    },
    "report_runs_by_report_key": {
        "title": "Report runs by report key",
        "description": "Execution volume and success counts from the report audit log.",
        "roles": ("DBA",),
        "sql": """
            SELECT report_key,
                COUNT(*) AS run_count,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) AS success_count
            FROM report_execution_logs
            GROUP BY report_key
            ORDER BY run_count DESC
        """,
        "params": [],
    },
    "schedules_overview": {
        "title": "Scheduled reports overview",
        "description": "All schedules with next/last run and last error (operator health).",
        "roles": ("DBA",),
        "sql": """
            SELECT id, report_key, cadence, is_enabled, next_run_at, last_run_at, last_error
            FROM report_schedules
            ORDER BY next_run_at ASC, id ASC
        """,
        "params": [],
    },
    "users_by_role": {
        "title": "Users by role",
        "description": "Headcount by RBAC role (no email addresses).",
        "roles": ("DBA",),
        "sql": """
            SELECT role, COUNT(*) AS user_count
            FROM users
            GROUP BY role
            ORDER BY role ASC
        """,
        "params": [],
    },
    "incident_history_by_action": {
        "title": "Incident history by action",
        "description": "Volume of incident audit events grouped by action type.",
        "roles": ("DBA", "Analyst"),
        "sql": """
            SELECT action, COUNT(*) AS event_count
            FROM incident_history
            GROUP BY action
            ORDER BY event_count DESC, action ASC
        """,
        "params": [],
    },
    "admin_audit_by_action": {
        "title": "User admin audit by action",
        "description": "Volume of DBA user-administration events grouped by action.",
        "roles": ("DBA",),
        "sql": """
            SELECT action, COUNT(*) AS event_count
            FROM user_admin_audit_logs
            GROUP BY action
            ORDER BY event_count DESC, action ASC
        """,
        "params": [],
    },
}


def get_report(report_key: str) -> dict[str, Any] | None:
    return REPORTS.get(report_key)
