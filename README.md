# logaudit — zero-dependency log validation, reporting & regression gates

[![ci](https://github.com/midat-fx/jsonl-log-auditor/actions/workflows/ci.yml/badge.svg)](https://github.com/midat-fx/jsonl-log-auditor/actions/workflows/ci.yml)
[![python: 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![deps: none](https://img.shields.io/badge/runtime%20deps-none-brightgreen.svg)](#zero-dependencies)
[![types: mypy strict](https://img.shields.io/badge/mypy-strict-blue.svg)](pyproject.toml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Parse, validate, report on, query, and **gate** structured logs from one CLI —
with **zero runtime dependencies** (Python standard library only) and
**byte-deterministic** output you can commit and diff in CI.

```console
$ logaudit report logs/*.jsonl -o out
$ logaudit regress out/report.json --baseline baselines/baseline.json
DRIFT: 1 metric(s) exceeded tolerance
  service.api.error_rate: 0.05 -> 0.19 (|delta|=280.00% > tol 10%)   # exit 1
```

## Why

Log checks that live in CI usually pull in a heavy stack. logaudit is a single
`pip install` with **nothing behind it** — pure stdlib — so it runs anywhere a
Python interpreter does. Its reports contain no timestamps or hostnames, so a
committed `report.json` changes only when your logs' *shape* changes, which is
exactly what makes `regress` a trustworthy gate.

## Install

```bash
pip install -e .            # from a clone
# or, once published:
# pip install logaudit
```

### Zero dependencies

The runtime depends on the standard library only (`argparse`, `json`, `re`,
`hashlib`, `gzip`, …). Dev extras (`pip install -e ".[dev]"`) add pytest, mypy,
and ruff — never required to *run* logaudit.

## Commands

| Command    | What it does                                                            |
|------------|-------------------------------------------------------------------------|
| `parse`    | Normalize JSONL / logfmt / nginx / CSV into canonical JSONL.            |
| `validate` | Check records against a [JSON-Schema subset](docs/schema-subset.md); exit 1 on any violation. |
| `report`   | Deterministic `report.json` + `report.md`: per-service error rates and p50/p95/p99. |
| `regress`  | Compare a report to a baseline; exit 1 if any metric drifts beyond tolerance. |
| `query`    | Filter records with a small [query language](docs/query-language.md).   |
| `redact`   | Mask PII (email / IPv4 / card) with a keyed HMAC — deterministic and joinable. |

Inputs may be multiple files, `-` for stdin, or `.gz` (transparent). Format is
auto-detected per file; override with `--format`.

## The query language

A real lexer + recursive-descent parser + evaluator — not a regex hack:

```console
$ logaudit query 'level=ERROR AND (latency_ms>500 OR code=~"5..") AND NOT service=probe' logs/app.jsonl
{"code":500,"latency_ms":231.1,"level":"ERROR","service":"worker","ts":"2026-01-01T00:01:24Z", ...}
$ logaudit query 'code>=400' logs/app.jsonl --count
281
```

Operators: `= != > >= < <= =~` (regex). `AND` binds tighter than `OR`; use
parentheses to override. Dotted fields (`http.status`) descend into nested
objects. Full grammar in [docs/query-language.md](docs/query-language.md).

## Validate as a gate

```console
$ logaudit validate logs/app.jsonl --schema schema.json
  logs/app.jsonl:3: level: value 'LOUD' not in enum ['DEBUG', 'INFO', 'WARN', 'ERROR']
  logs/app.jsonl:29: latency_ms: -5 < minimum 0
$ echo $?
1
```

## Report

```console
$ logaudit report logs/app.jsonl -o out && cat out/report.md
```

| service | count | errors | error_rate | p50 | p95 | p99 |
|---|---|---|---|---|---|---|
| api | 361 | 29 | 0.08 | 64.8 | 130.2 | 156.9 |
| worker | 385 | 36 | 0.09 | 205.8 | 273.7 | 295.9 |

Percentiles use the nearest-rank method (no interpolation), so every value is
an observed measurement and identical across platforms.

## Redaction

```console
$ echo '{"msg":"login from 10.0.0.5 by a@b.com"}' | logaudit redact - --key "$SECRET"
{"msg":"login from <ipv4:9d8a211029> by <email:454983b443>"}
```

The same value under the same key always maps to the same token, so redacted
logs stay joinable; the original is not recoverable and the key is never
written out.

## Determinism

Reports and parsed output are byte-stable: `json.dumps(sort_keys=True)`, fixed
float precision, nearest-rank percentiles, hour buckets by lexical slice, and no
wall-clock or host data anywhere. See [docs/determinism.md](docs/determinism.md).
The repo dogfoods this: CI runs `report` on the sample logs and `regress`es the
result against the committed baseline — if output ever drifts, the build fails.

## Develop

```bash
make install      # pip install -e ".[dev]"
make check        # ruff + mypy --strict + pytest
make all          # check + the report/regress self-gate
```

Quality bar: `ruff` clean, `mypy --strict` clean, ~93% test coverage, matrixed
on Python 3.11–3.13.

## Roadmap

Tracked as GitHub issues: multi-line stack-trace grouping, `sessionize` by
trace id, EWMA anomaly flags, and PyPI publishing via trusted publishing.

## License

MIT © Midat Faizov. A public, clean-room implementation demonstrating
stdlib-only tooling, a hand-written query language, and deterministic reporting.
