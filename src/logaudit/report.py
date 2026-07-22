"""Aggregate canonical records into a deterministic report (JSON + Markdown)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

from .percentile import nearest_rank
from .records import code_of, hour_of, is_error, latency_of, level_of, service_of
from .util import round2

Record = dict[str, Any]


def _top_n(counter: Counter[str], n: int) -> list[list[Any]]:
    ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    return [[k, c] for k, c in ranked[:n]]


def build_report(records: Iterable[Record], malformed: int) -> dict[str, Any]:
    svc_count: Counter[str] = Counter()
    svc_errors: Counter[str] = Counter()
    svc_lat: dict[str, list[float]] = {}
    levels: Counter[str] = Counter()
    codes: Counter[str] = Counter()
    by_hour: Counter[str] = Counter()
    total = 0

    for rec in records:
        total += 1
        svc = service_of(rec)
        svc_count[svc] += 1
        if is_error(rec):
            svc_errors[svc] += 1
        lat = latency_of(rec)
        if lat is not None:
            svc_lat.setdefault(svc, []).append(lat)
        levels[level_of(rec)] += 1
        code = code_of(rec)
        if code is not None:
            codes[str(code)] += 1
        hour = hour_of(rec)
        if hour is not None:
            by_hour[hour] += 1

    services: dict[str, Any] = {}
    for svc in svc_count:
        count = svc_count[svc]
        lats = svc_lat.get(svc, [])
        services[svc] = {
            "count": count,
            "errors": svc_errors[svc],
            "error_rate": round2(svc_errors[svc] / count) if count else 0.0,
            "latency_p50": round2(nearest_rank(lats, 0.50)),
            "latency_p95": round2(nearest_rank(lats, 0.95)),
            "latency_p99": round2(nearest_rank(lats, 0.99)),
        }

    return {
        "totals": {"records": total, "malformed": malformed},
        "services": services,
        "levels": dict(levels),
        "codes_top": _top_n(codes, 10),
        "by_hour": dict(by_hour),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    t = report["totals"]
    lines.append("# Log Report")
    lines.append("")
    lines.append(f"- records: {t['records']}")
    lines.append(f"- malformed: {t['malformed']}")
    lines.append("")
    lines.append("## Services")
    lines.append("")
    lines.append("| service | count | errors | error_rate | p50 | p95 | p99 |")
    lines.append("|---|---|---|---|---|---|---|")
    for svc in sorted(report["services"]):
        s = report["services"][svc]
        lines.append(
            f"| {svc} | {s['count']} | {s['errors']} | {s['error_rate']} | "
            f"{s['latency_p50']} | {s['latency_p95']} | {s['latency_p99']} |"
        )
    lines.append("")
    lines.append("## Levels")
    lines.append("")
    for lvl in sorted(report["levels"]):
        lines.append(f"- {lvl}: {report['levels'][lvl]}")
    lines.append("")
    lines.append("## Top status codes")
    lines.append("")
    for code, count in report["codes_top"]:
        lines.append(f"- {code}: {count}")
    lines.append("")
    return "\n".join(lines) + "\n"
