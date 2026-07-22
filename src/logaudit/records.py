"""Canonical field extraction over heterogeneous log records.

Log records vary; these helpers read the common observability fields with
sensible fallbacks so report/query/regress work across formats.
"""

from __future__ import annotations

from typing import Any

Record = dict[str, Any]

_ERROR_LEVELS = {"ERROR", "ERR", "CRITICAL", "CRIT", "FATAL", "EMERGENCY", "ALERT"}


def level_of(rec: Record) -> str:
    return str(rec.get("level", rec.get("severity", "UNKNOWN"))).upper()


def service_of(rec: Record) -> str:
    return str(rec.get("service", rec.get("svc", rec.get("app", "unknown"))))


def code_of(rec: Record) -> int | None:
    for k in ("code", "status", "status_code"):
        v = rec.get(k)
        if isinstance(v, bool):
            continue
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
    return None


def is_error(rec: Record) -> bool:
    if level_of(rec) in _ERROR_LEVELS:
        return True
    code = code_of(rec)
    return code is not None and code >= 500


def latency_of(rec: Record) -> float | None:
    for k in ("latency_ms", "latency", "duration_ms", "elapsed_ms", "response_time"):
        v = rec.get(k)
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                continue
    return None


def hour_of(rec: Record) -> str | None:
    """Bucket by hour using a lexical slice of the ISO timestamp (no tz math)."""
    ts = rec.get("ts", rec.get("timestamp", rec.get("time")))
    if not isinstance(ts, str) or len(ts) < 13:
        return None
    if ts[4] == "-" and ts[7] == "-" and ts[10] in ("T", " "):
        return ts[:13].replace(" ", "T")
    return None


def msg_of(rec: Record) -> str:
    return str(rec.get("msg", rec.get("message", "")))
