import json
import re
import time
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import ReportExecutionLog, User
from .report_catalog import get_report

MAX_ROWS_RETURNED = 500


def _normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip())


def _validate_sql_read_only(sql: str) -> None:
    normalized = _normalize_sql(sql).lower()
    if not normalized.startswith("select"):
        raise ValueError("Report SQL must be a SELECT statement")
    spaced = f" {normalized} "
    forbidden = (
        " insert ",
        " update ",
        " delete ",
        " merge ",
        " truncate ",
        " alter ",
        " drop ",
        " create ",
        " grant ",
        " revoke ",
        " copy ",
    )
    for phrase in forbidden:
        if phrase in spaced:
            raise ValueError("Report SQL contains disallowed constructs")


def _coerce_params(spec: dict[str, Any], raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(raw or {})
    param_defs = {p["name"]: p for p in spec["params"]}
    unknown = set(raw) - set(param_defs)
    if unknown:
        raise ValueError(f"Unknown parameters: {sorted(unknown)}")
    out: dict[str, Any] = {}
    for name, pdef in param_defs.items():
        if name in raw:
            val = raw[name]
        elif "default" in pdef:
            val = pdef["default"]
        else:
            raise ValueError(f"Missing parameter: {name}")
        typ = pdef["type"]
        if typ == "int":
            if isinstance(val, bool):
                raise ValueError(f"Parameter {name} must be an integer")
            coerced: int
            if isinstance(val, int):
                coerced = val
            elif isinstance(val, float) and val.is_integer():
                coerced = int(val)
            elif isinstance(val, str) and val.strip().lstrip("-").isdigit():
                coerced = int(val.strip())
            else:
                raise ValueError(f"Parameter {name} must be an integer")
            mn = pdef.get("min")
            mx = pdef.get("max")
            if mn is not None and coerced < mn:
                raise ValueError(f"Parameter {name} must be >= {mn}")
            if mx is not None and coerced > mx:
                raise ValueError(f"Parameter {name} must be <= {mx}")
            out[name] = coerced
        else:
            raise ValueError(f"Unsupported parameter type: {typ}")
    return out


def _jsonify_cell(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, memoryview)):
        return None
    return value


def execute_whitelisted_report(
    db: Session,
    user: User,
    report_key: str,
    raw_params: dict[str, Any] | None,
) -> dict[str, Any]:
    spec = get_report(report_key)
    if spec is None:
        raise ValueError(f"Unknown report: {report_key}")
    if user.role not in spec["roles"]:
        raise PermissionError("Role cannot run this report")

    sql = spec["sql"].strip()
    _validate_sql_read_only(sql)
    bind_params = _coerce_params(spec, raw_params)

    started = time.perf_counter()
    log_entry = ReportExecutionLog(
        user_id=user.id,
        report_key=report_key,
        params_json=json.dumps(bind_params, sort_keys=True),
    )

    try:
        result = db.execute(text(sql), bind_params)
        columns = list(result.keys())
        mappings = result.mappings().all()
        truncated = len(mappings) > MAX_ROWS_RETURNED
        rows_slice = mappings[:MAX_ROWS_RETURNED]
        rows = [{k: _jsonify_cell(row[k]) for k in columns} for row in rows_slice]
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        log_entry.row_count = len(rows)
        log_entry.duration_ms = elapsed_ms
        log_entry.success = True
        db.add(log_entry)
        db.commit()

        return {
            "report_key": report_key,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
            "duration_ms": elapsed_ms,
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        db.rollback()
        log_entry.duration_ms = elapsed_ms
        log_entry.success = False
        log_entry.row_count = None
        log_entry.error_message = str(exc)[:4000]
        db.add(log_entry)
        db.commit()
        raise
