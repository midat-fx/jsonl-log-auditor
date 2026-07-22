"""Command-line interface for logaudit."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

from . import __version__
from .parse import FORMATS, ParsedRecord, parse_stream
from .query import QueryError, compile_query
from .redact import build_redactor, redact_record
from .regress import regress
from .report import build_report, render_markdown
from .schema import validate_record
from .util import dumps, dumps_pretty, read_lines


def _iter_parsed(paths: list[str], fmt: str) -> Iterator[tuple[str, int, ParsedRecord]]:
    """Parse each file independently (format detected per file); yield (path, index, record)."""
    for path in paths:
        for idx, pr in enumerate(parse_stream(read_lines(path), fmt), start=1):
            yield (path, idx, pr)


@contextlib.contextmanager
def _open_out(path: str | None) -> Iterator[TextIO]:
    """Stream to a file, or stdout when path is falsy."""
    if path:
        with Path(path).open("w", encoding="utf-8") as fh:
            yield fh
    else:
        yield sys.stdout


def cmd_parse(args: argparse.Namespace) -> int:
    n = malformed = 0
    with _open_out(args.output) as out:
        for _path, _idx, pr in _iter_parsed(args.files, args.format):
            if pr.record is None:
                malformed += 1
                continue
            out.write(dumps(pr.record) + "\n")
            n += 1
    print(f"logaudit parse: {n} record(s), {malformed} malformed", file=sys.stderr)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    bad = shown = 0
    for path, idx, pr in _iter_parsed(args.files, args.format):
        if pr.record is None:
            bad += 1
            if shown < args.limit:
                print(f"  {path}:{idx}: {pr.error}")
                shown += 1
            continue
        violations = validate_record(pr.record, schema)
        if violations:
            bad += 1
            for v in violations:
                if shown < args.limit:
                    print(f"  {path}:{idx}: {v}")
                    shown += 1
    print(f"logaudit validate: {bad} bad record(s) (max-bad {args.max_bad})", file=sys.stderr)
    return 1 if bad > args.max_bad else 0


def cmd_report(args: argparse.Namespace) -> int:
    records = []
    malformed = 0
    for _path, _idx, pr in _iter_parsed(args.files, args.format):
        if pr.record is None:
            malformed += 1
        else:
            records.append(pr.record)
    rep = build_report(records, malformed)
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "report.json").write_text(dumps_pretty(rep) + "\n", encoding="utf-8")
    (outdir / "report.md").write_text(render_markdown(rep), encoding="utf-8")
    print(f"logaudit report: wrote {outdir}/report.json and report.md", file=sys.stderr)
    return 0


def cmd_regress(args: argparse.Namespace) -> int:
    current = json.loads(Path(args.report).read_text(encoding="utf-8"))
    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    per_metric = None
    if args.per_metric:
        per_metric = json.loads(Path(args.per_metric).read_text(encoding="utf-8"))
    ok, drift = regress(current, baseline, tol=args.tol, per_metric=per_metric)
    for d in drift:
        print(f"  {d}")
    print("OK: no drift" if ok else f"DRIFT: {len(drift)} metric(s) exceeded tolerance")
    return 0 if ok else 1


def cmd_query(args: argparse.Namespace) -> int:
    try:
        query = compile_query(args.expr)
    except QueryError as e:
        print(f"query error: {e}", file=sys.stderr)
        return 2
    n = matched = 0
    for _path, _idx, pr in _iter_parsed(args.files, args.format):
        if pr.record is None:
            continue
        n += 1
        if query.matches(pr.record):
            matched += 1
            if not args.count:
                print(dumps(pr.record))
    if args.count:
        print(matched)
    print(f"logaudit query: {matched}/{n} matched", file=sys.stderr)
    return 0


def cmd_redact(args: argparse.Namespace) -> int:
    key = (args.key or os.environ.get("LOGAUDIT_REDACT_KEY") or "logaudit-demo-key").encode()
    patterns = None
    if args.rules:
        patterns = json.loads(Path(args.rules).read_text(encoding="utf-8"))["patterns"]
    rules = build_redactor(key, patterns)
    for _path, _idx, pr in _iter_parsed(args.files, args.format):
        if pr.record is None:
            continue
        print(dumps(redact_record(pr.record, key, rules)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="logaudit",
        description="Validate, report on, query, and gate structured logs. Zero dependencies.",
    )
    p.add_argument("--version", action="version", version=f"logaudit {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    def with_inputs(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("files", nargs="+", help="log files ('-' for stdin, .gz supported)")
        sp.add_argument("--format", choices=FORMATS, default="auto")

    sp = sub.add_parser("parse", help="normalize logs to canonical JSONL")
    with_inputs(sp)
    sp.add_argument("-o", "--output", help="output file (default: stdout)")

    sp = sub.add_parser("validate", help="validate records against a JSON schema subset")
    with_inputs(sp)
    sp.add_argument("--schema", required=True)
    sp.add_argument("--max-bad", type=int, default=0, dest="max_bad")
    sp.add_argument("--limit", type=int, default=50, help="max messages to print")

    sp = sub.add_parser("report", help="write report.json and report.md")
    with_inputs(sp)
    sp.add_argument("-o", "--output", default="report", help="output directory")

    sp = sub.add_parser("regress", help="gate a report against a baseline")
    sp.add_argument("report", help="report.json produced by 'report'")
    sp.add_argument("--baseline", required=True)
    sp.add_argument("--tol", type=float, default=0.10, help="relative tolerance (default 0.10)")
    sp.add_argument("--per-metric", dest="per_metric", help="JSON of {metric: tolerance}")

    sp = sub.add_parser("query", help="filter records with the query language")
    sp.add_argument("expr", help="query expression")
    sp.add_argument("files", nargs="+")
    sp.add_argument("--format", choices=FORMATS, default="auto")
    sp.add_argument("--count", action="store_true", help="print only the match count")

    sp = sub.add_parser("redact", help="mask PII deterministically (HMAC)")
    with_inputs(sp)
    sp.add_argument("--key", help="HMAC key (or env LOGAUDIT_REDACT_KEY)")
    sp.add_argument("--rules", help='JSON file with {"patterns": {name: regex}}')

    return p


_HANDLERS = {
    "parse": cmd_parse,
    "validate": cmd_validate,
    "report": cmd_report,
    "regress": cmd_regress,
    "query": cmd_query,
    "redact": cmd_redact,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return _HANDLERS[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
