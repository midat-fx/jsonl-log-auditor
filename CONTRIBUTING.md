# Contributing

## Setup

```bash
python -m venv .venv && . .venv/bin/activate
make install        # pip install -e ".[dev]"
make check          # ruff + mypy --strict + pytest
```

## Rules of the house

- **Zero runtime dependencies.** The `logaudit` package imports only the Python
  standard library. Dev tooling (pytest/mypy/ruff) is fine; runtime deps are not.
- **Determinism is a feature.** New serialized output must be byte-stable and
  free of timestamps/hostnames. Add a test that builds it twice and compares.
- **Typed and linted.** `mypy --strict` and `ruff` must pass; run `ruff format`.
- **Tested.** Coverage is gated at 85% in CI. New behaviour ships with tests.

## Regenerating sample data

```bash
python tools/gen_logs.py            # rewrites logs/*.jsonl deterministically
logaudit report logs/sample_app.jsonl -o out
cp out/report.json baselines/baseline.json   # only if the report shape changed
```
