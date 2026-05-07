"""Predefined read-only SQL reports (whitelist). Only these queries may run via /reports/run."""

from typing import Any

# Each report: title, description, allowed roles, SQL (must be SELECT-only), param specs.
REPORTS: dict[str, dict[str, Any]] = {
    "incidents_by_status": {
        "title": "Incidents by status",
        "description": "Count of incidents grouped by workflow status.",
        "roles": ("DBA", "Analyst", "Viewer"),
        "sql": """
            SELECT status, COUNT(*)::bigint AS incident_count
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
}


def get_report(report_key: str) -> dict[str, Any] | None:
    return REPORTS.get(report_key)
