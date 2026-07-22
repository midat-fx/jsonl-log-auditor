"""Compare a report against a baseline and flag metric drift.

This is what makes logaudit a CI gate: run ``report`` on fresh logs, then
``regress`` the result against a committed baseline. Any metric that moves by
more than the tolerance fails the build.
"""

from __future__ import annotations

from typing import Any


def flatten(report: dict[str, Any]) -> dict[str, float]:
    """Flatten a report into a comparable name -> number map."""
    out: dict[str, float] = {
        "totals.records": float(report["totals"]["records"]),
        "totals.malformed": float(report["totals"]["malformed"]),
    }
    for svc, s in report.get("services", {}).items():
        out[f"service.{svc}.count"] = float(s["count"])
        out[f"service.{svc}.error_rate"] = float(s["error_rate"])
        out[f"service.{svc}.latency_p95"] = float(s["latency_p95"])
    return out


def regress(
    current: dict[str, Any],
    baseline: dict[str, Any],
    tol: float = 0.10,
    per_metric: dict[str, float] | None = None,
) -> tuple[bool, list[str]]:
    """Return (ok, drift_messages). ok is True when nothing exceeds tolerance."""
    per_metric = per_metric or {}
    cur, base = flatten(current), flatten(baseline)
    drift: list[str] = []
    for name in sorted(set(cur) | set(base)):
        c = cur.get(name)
        b = base.get(name)
        if b is None:
            drift.append(f"{name}: new metric (now {c})")
            continue
        if c is None:
            drift.append(f"{name}: present in baseline ({b}), missing now")
            continue
        t = per_metric.get(name, tol)
        rel = abs(c - b) / max(abs(b), 1e-9)
        if rel > t:
            drift.append(f"{name}: {b} -> {c} (|delta|={rel:.2%} > tol {t:.0%})")
    return (len(drift) == 0, drift)
