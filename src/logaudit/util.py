"""Deterministic helpers shared across logaudit.

Every serialized artifact in logaudit is byte-stable: JSON is dumped with sorted
keys and compact separators, floats are rounded to a fixed precision, and no
timestamps, hostnames, or run IDs ever enter the output. That makes reports safe
to commit and to diff in CI.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def dumps(obj: Any) -> str:
    """Canonical JSON: sorted keys, compact, UTF-8, deterministic."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def dumps_pretty(obj: Any) -> str:
    """Human-readable canonical JSON (sorted keys, 2-space indent)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2)


def round2(x: float) -> float:
    """Round to two decimals; -0.0 is normalized to 0.0 for stable output."""
    r = round(float(x), 2)
    return 0.0 if r == 0.0 else r


def read_lines(path: str) -> Iterator[str]:
    """Yield lines from a file, transparently decompressing .gz. '-' is stdin."""
    if path == "-":
        import sys

        yield from (line.rstrip("\n") for line in sys.stdin)
        return
    p = Path(path)
    if p.suffix == ".gz":
        with gzip.open(p, "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                yield line.rstrip("\n")
    else:
        with p.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                yield line.rstrip("\n")
