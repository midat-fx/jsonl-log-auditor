#!/usr/bin/env python3
"""Generate deterministic sample logs for logaudit (committed to logs/).

Seeded and time-stamped from a fixed base instant, so re-running produces
byte-identical files. Not used in CI — the committed output is what tests read.

Usage: python3 tools/gen_logs.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

BASE_EPOCH = "2026-01-01T00:00:00"
SERVICES = ["api", "web", "worker", "auth"]
ROOT = Path(__file__).resolve().parent.parent


def _ts(i: int) -> str:
    # Deterministic ISO timestamp: base date, +i*7 seconds, spread across ~3 hours.
    total = i * 7
    hh = (total // 3600) % 24
    mm = (total // 60) % 60
    ss = total % 60
    return f"2026-01-01T{hh:02d}:{mm:02d}:{ss:02d}Z"


def _record(rng: random.Random, i: int) -> dict[str, object]:
    service = rng.choice(SERVICES)
    roll = rng.random()
    if roll < 0.80:
        level, code = "INFO", 200
    elif roll < 0.92:
        level, code = "WARN", rng.choice([301, 404, 429])
    else:
        level, code = "ERROR", rng.choice([500, 502, 503])
    latency = round(abs(rng.gauss(60 if service != "worker" else 200, 40)) + 5, 1)
    return {
        "ts": _ts(i),
        "level": level,
        "service": service,
        "code": code,
        "latency_ms": latency,
        "trace_id": f"{rng.getrandbits(32):08x}",
        "msg": f"{level.lower()} handling request on {service}",
    }


def main() -> None:
    rng = random.Random(42)
    good = [json.dumps(_record(rng, i), sort_keys=True) for i in range(1500)]
    (ROOT / "logs" / "sample_app.jsonl").write_text("\n".join(good) + "\n", encoding="utf-8")

    # A small "bad" file: valid records interleaved with malformed and invalid ones.
    rng_bad = random.Random(7)
    bad_lines: list[str] = []
    for i in range(200):
        r = rng_bad.random()
        if r < 0.05:
            bad_lines.append('{"ts":"2026-01-01T00:00:00Z","level":"INFO"')  # truncated JSON
        elif r < 0.10:
            rec = _record(rng_bad, i)
            rec["level"] = "LOUD"  # not in enum
            bad_lines.append(json.dumps(rec, sort_keys=True))
        elif r < 0.15:
            rec = _record(rng_bad, i)
            rec["latency_ms"] = -5  # below minimum
            bad_lines.append(json.dumps(rec, sort_keys=True))
        else:
            bad_lines.append(json.dumps(_record(rng_bad, i), sort_keys=True))
    (ROOT / "logs" / "sample_bad.jsonl").write_text("\n".join(bad_lines) + "\n", encoding="utf-8")
    print("wrote logs/sample_app.jsonl and logs/sample_bad.jsonl")


if __name__ == "__main__":
    main()
