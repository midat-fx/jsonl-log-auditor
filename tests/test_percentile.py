from __future__ import annotations

import pytest

from logaudit.percentile import nearest_rank


def test_empty_is_zero() -> None:
    assert nearest_rank([], 0.5) == 0.0


def test_known_values() -> None:
    vals = list(range(1, 11))  # 1..10
    assert nearest_rank(vals, 0.5) == 5
    assert nearest_rank(vals, 0.9) == 9
    assert nearest_rank(vals, 0.95) == 10
    assert nearest_rank(vals, 0.0) == 1
    assert nearest_rank(vals, 1.0) == 10


def test_unsorted_input() -> None:
    assert nearest_rank([3, 1, 2], 0.5) == 2


def test_out_of_range() -> None:
    with pytest.raises(ValueError):
        nearest_rank([1, 2], 1.5)
