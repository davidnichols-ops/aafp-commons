.PHONY: test lint typecheck check build smoke schemas

test:
	uv run pytest -q

lint:
	uv run ruff check src tests examples

typecheck:
	uv run mypy src

check: test lint typecheck
	git diff --check

schemas:
	uv run python -c 'import json; from pathlib import Path; [json.loads(p.read_text()) for p in Path("protocols").glob("*.schema.json")]'

build:
	uv build

smoke:
	root=$$(mktemp -d); \
	uv run aafp-commons constitutions install-all "$$root" >/dev/null; \
	uv run aafp-commons constitutions verify "$$root" >/dev/null; \
	uv run aafp-commons protocols list >/dev/null; \
	uv run aafp-commons protocols show agent-join@1 >/dev/null; \
	uv run aafp-commons protocols show agent-join@1 --raw >/dev/null
