# Changelog

All notable changes are documented here, following
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-01

First stable release.

### Added
- `parse` — normalize JSONL, logfmt, nginx combined, and header CSV into
  canonical JSONL; per-file auto-detection; `.gz` and stdin input.
- `validate` — a documented JSON-Schema subset (type/enum/pattern/min/max/
  length/format); exits non-zero past `--max-bad`.
- `report` — deterministic `report.json` + `report.md` with per-service error
  rates and nearest-rank p50/p95/p99.
- `regress` — baseline comparison with global and per-metric tolerances; the CI
  gate.
- `query` — a lexer + recursive-descent parser + evaluator for a small filter
  language (`AND`/`OR`/`NOT`, `=~`, dotted fields).
- `redact` — deterministic, joinable PII masking via keyed HMAC.
- Zero runtime dependencies; `mypy --strict`; ~93% coverage; Python 3.11–3.13.

## Roadmap

Tracked as GitHub issues: multi-line stack-trace grouping, `sessionize` by trace
id, EWMA anomaly detection, and PyPI trusted publishing.
