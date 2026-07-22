from __future__ import annotations

from pathlib import Path

from logaudit.parse import parse_stream
from logaudit.report import build_report, render_markdown
from logaudit.util import dumps_pretty

DATA = Path(__file__).parent / "data"


def _small() -> list[dict]:
    lines = (DATA / "small.jsonl").read_text().splitlines()
    return [pr.record for pr in parse_stream(lines) if pr.record is not None]


def test_report_values() -> None:
    rep = build_report(_small(), 0)
    assert rep["totals"] == {"records": 3, "malformed": 0}
    api = rep["services"]["api"]
    assert api["count"] == 2 and api["errors"] == 1 and api["error_rate"] == 0.5
    assert api["latency_p50"] == 10 and api["latency_p95"] == 30
    assert rep["services"]["web"]["error_rate"] == 0.0
    assert rep["levels"] == {"INFO": 2, "ERROR": 1}
    assert rep["codes_top"] == [["200", 2], ["500", 1]]
    assert rep["by_hour"] == {"2026-01-01T00": 2, "2026-01-01T01": 1}


def test_report_deterministic() -> None:
    recs = _small()
    assert dumps_pretty(build_report(recs, 0)) == dumps_pretty(build_report(recs, 0))


def test_markdown_renders() -> None:
    md = render_markdown(build_report(_small(), 0))
    assert "# Log Report" in md and "| api |" in md
