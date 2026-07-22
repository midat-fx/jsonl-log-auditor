from __future__ import annotations

from pathlib import Path

import pytest

from logaudit.cli import main

ROOT = Path(__file__).parent.parent
GOOD = str(ROOT / "logs" / "sample_app.jsonl")
BAD = str(ROOT / "logs" / "sample_bad.jsonl")
SCHEMA = str(ROOT / "schema.json")


def test_validate_bad_exits_1() -> None:
    assert main(["validate", BAD, "--schema", SCHEMA]) == 1


def test_validate_good_exits_0() -> None:
    assert main(["validate", GOOD, "--schema", SCHEMA]) == 0


def test_report_is_deterministic(tmp_path: Path) -> None:
    main(["report", GOOD, "-o", str(tmp_path / "a")])
    main(["report", GOOD, "-o", str(tmp_path / "b")])
    a = (tmp_path / "a" / "report.json").read_bytes()
    b = (tmp_path / "b" / "report.json").read_bytes()
    assert a == b


def test_committed_baseline_matches_report(tmp_path: Path) -> None:
    main(["report", GOOD, "-o", str(tmp_path / "r")])
    produced = (tmp_path / "r" / "report.json").read_text()
    committed = (ROOT / "baselines" / "baseline.json").read_text()
    assert produced == committed


def test_regress_self_is_ok(tmp_path: Path) -> None:
    main(["report", GOOD, "-o", str(tmp_path / "r")])
    rj = str(tmp_path / "r" / "report.json")
    assert main(["regress", rj, "--baseline", rj]) == 0


def test_query_count(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["query", "level=ERROR", GOOD, "--count"])
    out = capsys.readouterr().out.strip().splitlines()
    assert rc == 0 and int(out[0]) > 0


def test_query_bad_expr_exits_2() -> None:
    assert main(["query", "level=", GOOD]) == 2


def test_redact_roundtrip(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    f = tmp_path / "in.jsonl"
    f.write_text('{"msg":"login from 10.0.0.5 by a@b.com"}\n')
    assert main(["redact", str(f), "--key", "k"]) == 0
    out = capsys.readouterr().out
    assert "<ipv4:" in out and "<email:" in out and "a@b.com" not in out
