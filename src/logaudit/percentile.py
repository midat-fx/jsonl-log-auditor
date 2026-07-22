"""Nearest-rank percentiles.

Deterministic and dependency-free: no interpolation, so the result is always an
observed value and identical across platforms and Python versions.
"""

from __future__ import annotations

from collections.abc import Sequence


def nearest_rank(values: Sequence[float], q: float) -> float:
    """Return the q-quantile (0..1) of values by the nearest-rank method.

    rank = ceil(q * n), clamped to [1, n]; the value at that 1-based rank is
    returned. An empty sequence yields 0.0.
    """
    if not 0.0 <= q <= 1.0:
        raise ValueError(f"q must be in [0, 1], got {q}")
    n = len(values)
    if n == 0:
        return 0.0
    ordered = sorted(values)
    import math

    rank = max(1, min(n, math.ceil(q * n)))
    return float(ordered[rank - 1])
