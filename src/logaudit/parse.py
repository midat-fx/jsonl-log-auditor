"""Multi-format log ingest into a canonical record stream.

Supports JSONL, logfmt, nginx combined access logs, and header CSV. The format
is detected once from the first non-blank line (override with ``fmt``) and
applied to the whole stream. Malformed lines never abort parsing: they are
yielded with ``record=None`` and an ``error`` string so callers can count and
report them.
"""

from __future__ import annotations

import csv as _csv
import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

Record = dict[str, Any]

FORMATS = ("auto", "jsonl", "logfmt", "nginx", "csv")


@dataclass
class ParsedRecord:
    raw: str
    record: Record | None
    error: str | None


_NGINX = re.compile(
    r"^(?P<remote>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "
    r'"(?P<method>\S+) (?P<path>\S+) (?P<proto>[^"]+)" '
    r"(?P<status>\d{3}) (?P<bytes>\d+|-) "
    r'"(?P<referer>[^"]*)" "(?P<agent>[^"]*)"'
)
_LOGFMT_PAIR = re.compile(r'(\w[\w.\-]*)=("(?:[^"\\]|\\.)*"|\S+)')
_INT = re.compile(r"-?\d+")
_FLOAT = re.compile(r"-?\d*\.\d+|-?\d+\.\d*")


def _coerce(s: str) -> Any:
    low = s.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if _INT.fullmatch(s):
        return int(s)
    if _FLOAT.fullmatch(s):
        return float(s)
    return s


def detect_format(line: str) -> str:
    """Guess the format of a single line (never returns 'auto')."""
    if line.lstrip().startswith("{"):
        return "jsonl"
    if _NGINX.match(line):
        return "nginx"
    tokens = line.split()
    if tokens and "=" in tokens[0] and _LOGFMT_PAIR.match(tokens[0]):
        return "logfmt"
    if "," in line:
        return "csv"
    return "jsonl"


def _parse_jsonl(line: str) -> ParsedRecord:
    try:
        obj = json.loads(line)
    except json.JSONDecodeError as e:
        return ParsedRecord(line, None, f"invalid json: {e.msg}")
    if not isinstance(obj, dict):
        return ParsedRecord(line, None, "json value is not an object")
    return ParsedRecord(line, obj, None)


def _parse_logfmt(line: str) -> ParsedRecord:
    rec: Record = {}
    for m in _LOGFMT_PAIR.finditer(line):
        key, val = m.group(1), m.group(2)
        if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
            rec[key] = val[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        else:
            rec[key] = _coerce(val)
    if not rec:
        return ParsedRecord(line, None, "no logfmt key=value pairs")
    return ParsedRecord(line, rec, None)


def _parse_nginx(line: str) -> ParsedRecord:
    m = _NGINX.match(line)
    if not m:
        return ParsedRecord(line, None, "does not match nginx combined format")
    status = int(m.group("status"))
    level = "ERROR" if status >= 500 else "WARN" if status >= 400 else "INFO"
    rec: Record = {
        "ts": m.group("time"),
        "service": "nginx",
        "level": level,
        "code": status,
        "method": m.group("method"),
        "path": m.group("path"),
        "remote": m.group("remote"),
        "msg": f"{m.group('method')} {m.group('path')} {status}",
    }
    nbytes = m.group("bytes")
    if nbytes != "-":
        rec["bytes"] = int(nbytes)
    return ParsedRecord(line, rec, None)


def _parse_one(line: str, fmt: str) -> ParsedRecord:
    if fmt == "jsonl":
        return _parse_jsonl(line)
    if fmt == "logfmt":
        return _parse_logfmt(line)
    if fmt == "nginx":
        return _parse_nginx(line)
    return ParsedRecord(line, None, f"unsupported format: {fmt}")


def parse_stream(lines: Iterable[str], fmt: str = "auto") -> Iterator[ParsedRecord]:
    """Parse a stream of raw log lines into ParsedRecords. Blank lines skipped."""
    if fmt not in FORMATS:
        raise ValueError(f"unknown format {fmt!r}; choose from {FORMATS}")
    it = iter(lines)
    first: str | None = None
    for raw in it:
        if raw.strip():
            first = raw
            break
    if first is None:
        return

    resolved = detect_format(first) if fmt == "auto" else fmt
    header: list[str] | None = None
    if resolved == "csv":
        header = next(_csv.reader([first]))
    else:
        yield _parse_one(first, resolved)

    for raw in it:
        if not raw.strip():
            continue
        if resolved == "csv":
            assert header is not None
            try:
                row = next(_csv.reader([raw]))
            except _csv.Error as e:
                yield ParsedRecord(raw, None, f"invalid csv: {e}")
                continue
            rec: Record = {header[i]: _coerce(row[i]) for i in range(min(len(header), len(row)))}
            yield ParsedRecord(raw, rec, None)
        else:
            yield _parse_one(raw, resolved)
