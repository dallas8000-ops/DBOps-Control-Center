"""DBA backup export — static SQL per table (no dynamic table names)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import TextClause

# Order preserved for deterministic JSON snapshots.
EXPORT_TABLE_NAMES: tuple[str, ...] = (
    "users",
    "incidents",
    "incident_history",
    "report_schedules",
    "report_execution_logs",
    "user_admin_audit_logs",
    "billing_settings",
    "onboarding_events",
)

_EXPORT_QUERIES: dict[str, TextClause] = {
    name: text(f"SELECT * FROM {name}")
    for name in EXPORT_TABLE_NAMES
}


def export_table_rows(db: Session, table: str) -> list[dict[str, Any]]:
    if table not in _EXPORT_QUERIES:
        raise ValueError(f"Unknown export table: {table}")
    rows = db.execute(_EXPORT_QUERIES[table]).mappings().all()
    return [dict(r) for r in rows]


def build_admin_export_snapshot(db: Session, *, exported_at: str) -> dict[str, Any]:
    snapshot: dict[str, Any] = {"exported_at": exported_at}
    for table in EXPORT_TABLE_NAMES:
        try:
            snapshot[table] = export_table_rows(db, table)
        except Exception as exc:
            snapshot[table] = {"error": str(exc)}
    return snapshot
