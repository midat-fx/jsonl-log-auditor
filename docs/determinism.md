# Determinism

logaudit's serialized output is byte-stable: the same input always produces the
same bytes, on any platform and Python version. That is what lets a `report.json`
be committed and a `regress` gate be trusted.

## How it is guaranteed

- **Canonical JSON** — `json.dumps(sort_keys=True, ensure_ascii=False,
  separators=(",",":"))` for machine output; sorted-key, indented JSON for
  reports. Dict insertion order never affects the bytes.
- **Fixed float precision** — metrics are rounded with a single helper
  (`round2`), and `-0.0` is normalized to `0.0`.
- **Nearest-rank percentiles** — no interpolation, so p50/p95/p99 are always
  observed values, not platform-dependent averages.
- **Lexical hour buckets** — `by_hour` slices the ISO timestamp string; no
  timezone arithmetic that could vary by locale.
- **No environment in output** — no timestamps, hostnames, PIDs, or run IDs.

## How it is tested

- `tests/test_report.py` asserts a second `build_report` is identical.
- `tests/test_cli.py::test_report_is_deterministic` writes two reports and
  compares the bytes.
- `tests/test_cli.py::test_committed_baseline_matches_report` asserts the report
  of the sample logs equals the committed `baselines/baseline.json`.
- CI dogfoods it: the `gate` job runs `report` then `regress` against the
  committed baseline, so any drift fails the build.
