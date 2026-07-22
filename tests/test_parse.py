from __future__ import annotations

import json
from pathlib import Path

from logaudit.parse import detect_format, parse_stream

DATA = Path(__file__).parent / "data"


def _records(lines: list[str], fmt: str = "auto") -> list[dict]:
    return [pr.record for pr in parse_stream(lines, fmt) if pr.record is not None]


def test_detect_format() -> None:
    assert detect_format('{"a":1}') == "jsonl"
    assert detect_format("level=info service=api") == "logfmt"
    assert detect_format('1.2.3.4 - - [x] "GET / HTTP/1.1" 200 1 "-" "-"') == "nginx"
    assert detect_format("a,b,c") == "csv"


def test_jsonl_roundtrip() -> None:
    recs = _records(['{"level":"INFO","n":1}', '{"level":"ERROR","n":2}'])
    assert recs == [{"level": "INFO", "n": 1}, {"level": "ERROR", "n": 2}]


def test_jsonl_malformed_is_counted_not_raised() -> None:
    parsed = list(parse_stream(['{"ok":1}', "{ broken", "not json at all"], "jsonl"))
    assert parsed[0].record == {"ok": 1}
    assert parsed[1].record is None and parsed[1].error
    assert parsed[2].record is None


def test_logfmt() -> None:
    (rec,) = _records(['level=info service=api latency_ms=12 msg="hello world"'], "logfmt")
    assert rec == {"level": "info", "service": "api", "latency_ms": 12, "msg": "hello world"}


def test_logfmt_coerces_types() -> None:
    (rec,) = _records(["ok=true count=3 ratio=0.5 name=api"], "logfmt")
    assert rec == {"ok": True, "count": 3, "ratio": 0.5, "name": "api"}


def test_nginx_combined() -> None:
    line = '10.0.0.9 - - [01/Jan/2026:00:00:01 +0000] "POST /login HTTP/1.1" 503 0 "-" "app/1.0"'
    (rec,) = _records([line], "nginx")
    assert rec["service"] == "nginx"
    assert rec["level"] == "ERROR"
    assert rec["code"] == 503
    assert rec["method"] == "POST" and rec["path"] == "/login"


def test_csv_with_header() -> None:
    recs = _records(["id,level,code", "1,INFO,200", "2,ERROR,500"], "csv")
    assert recs == [
        {"id": 1, "level": "INFO", "code": 200},
        {"id": 2, "level": "ERROR", "code": 500},
    ]


def test_blank_lines_skipped() -> None:
    assert _records(["", '{"a":1}', "   ", '{"b":2}']) == [{"a": 1}, {"b": 2}]


def test_parse_dump_parse_is_idempotent() -> None:
    lines = (DATA / "small.jsonl").read_text().splitlines()
    once = _records(lines)
    twice = _records([json.dumps(r, sort_keys=True) for r in once])
    assert once == twice


def test_fuzz_garbage_never_crashes() -> None:
    garbage = ["\x00\x01", "}{][", "a" * 5000, "", "𝕦𝕟𝕚𝕔𝕠𝕕𝕖", "{'single':1}"]
    parsed = list(parse_stream(garbage, "jsonl"))
    # No exception; every line is either a record or a counted malformed line.
    assert all((p.record is None) or isinstance(p.record, dict) for p in parsed)
