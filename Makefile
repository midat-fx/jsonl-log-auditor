.PHONY: install lint typecheck test check report gate all clean

install:
	pip install -e ".[dev]"

lint:
	ruff check src tests
	ruff format --check src tests

typecheck:
	mypy

test:
	pytest

check: lint typecheck test

report:
	logaudit report logs/sample_app.jsonl -o out

# Dogfood: the report of the sample logs must match the committed baseline.
gate: report
	logaudit regress out/report.json --baseline baselines/baseline.json

all: check gate

clean:
	rm -rf out report .coverage .mypy_cache .ruff_cache .pytest_cache
