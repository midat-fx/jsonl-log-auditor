from __future__ import annotations

import copy

from logaudit.regress import regress

BASE = {
    "totals": {"records": 100, "malformed": 0},
    "services": {
        "api": {"count": 100, "errors": 5, "error_rate": 0.05, "latency_p95": 50},
    },
}


def test_no_drift_vs_self() -> None:
    ok, drift = regress(BASE, BASE)
    assert ok and drift == []


def test_drift_detected() -> None:
    cur = copy.deepcopy(BASE)
    cur["services"]["api"]["error_rate"] = 0.50
    ok, drift = regress(cur, BASE, tol=0.10)
    assert not ok
    assert any("error_rate" in d for d in drift)


def test_per_metric_tolerance() -> None:
    cur = copy.deepcopy(BASE)
    cur["services"]["api"]["latency_p95"] = 60  # +20%
    assert not regress(cur, BASE, tol=0.10)[0]
    ok, _ = regress(cur, BASE, tol=0.10, per_metric={"service.api.latency_p95": 0.5})
    assert ok


def test_missing_metric() -> None:
    cur = copy.deepcopy(BASE)
    del cur["services"]["api"]
    ok, drift = regress(cur, BASE)
    assert not ok and any("missing now" in d for d in drift)
