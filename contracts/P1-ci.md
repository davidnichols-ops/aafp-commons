# P1-ci Contract — Continuous Integration Workflow

Status: implementation contract; P1-ci remains uncommitted until the conductor
authorizes a commit. This contract adds a CI workflow without publishing,
secrets, or network services.

## Objective

Provide a deterministic, offline CI workflow that runs the test suite, lint,
and the endpoint guard test on every push and pull request to `main`. The
workflow uses a temporary `COMMONS_HOME` so that no agent identity, ledger, or
simulation state is mutated on the runner or on the operator's machine.

## Deliverables

Ship the following in-tree, without registry or dependency changes:

- `.github/workflows/ci.yml` — the CI workflow described below.
- `contracts/P1-ci.md` — this file.

## Workflow requirements

- **Triggers**: `push` to `main` and `pull_request` to `main`. No other
  branches, no `workflow_dispatch`, no scheduled runs.
- **Permissions**: `contents: read` only. No write tokens, deploy keys, or
  secrets.
- **Environment**: `COMMONS_HOME` set to `$RUNNER_TEMP/commons-ci` for every
  step that executes tests or the commons CLI. No other environment overrides
  that mutate the simulation home.
- **Test step**: `uv run --no-sync pytest -q`. If the uv cache is unavailable,
  fall back to `python -m pytest -q`.
- **Lint step**: `ruff check` against `src`, `tests`, and `examples`.
- **Endpoint guard step**: run `tests/test_no_remote_endpoints.py`
  explicitly so the guard is visible as a distinct CI gate.
- **Setup**: `actions/checkout@v4`, `astral-sh/setup-uv@v6` with cache enabled,
  `uv python install 3.11`, and `uv sync --extra dev` to populate the
  environment before the `--no-sync` test run.

## Out of scope

- Secrets, deploy keys, publishing, or upload artifacts.
- Network services, Vast, SSH, QUIC, or mDNS.
- New MCP server names or MCP configuration changes.
- Simulation-home mutations beyond the temporary `COMMONS_HOME` on the runner.
- Modifying `README.md`, PASS logs, `pyproject.toml`, or any packaging config.
- Modifying tests beyond the requested workflow and contract.
- Running `git add -A` or any bulk staging operation.
- Building distributions, validating protocol schemas, or smoke-testing
  packaged constitutions (those remain in `quality.yml`).

## Acceptance

- `.github/workflows/ci.yml` exists and triggers on `push` and `pull_request`
  to `main` only.
- The workflow sets `COMMONS_HOME` to `$RUNNER_TEMP/commons-ci` for test and
  lint steps.
- The workflow runs `uv run --no-sync pytest -q` with a `python -m pytest`
  fallback, `ruff check`, and the endpoint guard test as distinct steps.
- The workflow declares `permissions: contents: read` and references no
  secrets, deploy keys, or publishing steps.
- The workflow does not invoke Vast, SSH, network services, or MCP tools.
- `contracts/P1-ci.md` exists and documents this contract.
- No files are staged or committed.
- No `README.md`, PASS log, packaging config, or test file is modified.
