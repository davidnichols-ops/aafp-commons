# R3 Offline Wheel-Install Regression Contract

Status: implementation contract; R3 remains uncommitted until the conductor
authorizes a commit. This contract verifies that the built wheel installs and
functions (import + Ironclad signing + `commons world`) in a fully offline,
isolated environment that never contacts `/Users/david/Projects` during the
test phase.

## Objective

Prove that `uv pip install dist/*.whl` followed by `import aafp_commons`,
Ironclad packet signing/verification, and `commons world` succeeds without
network access and without reading from the source tree at
`/Users/david/Projects`. The test stages only the built Commons wheel; its
vendored Ironclad compatibility package is inside that wheel. Installation
and functional checks run from `/tmp` with a clean `PYTHONPATH` and
`uv --offline`.

## Scope

- Stage `dist/aafp_commons-0.1.0-py3-none-any.whl` into
  `/tmp/commons-pass5-offline/wheels/` (setup phase only).
- Create an isolated venv at `/tmp/commons-pass5-offline/venv`.
- Install the aafp-commons wheel with `uv pip install --offline --find-links`
  from `/tmp`, with `PYTHONPATH` cleared and `cwd=/tmp`.
- Verify `aafp_commons.__file__` and `ironclad.__file__` resolve into the
  `/tmp` venv site-packages — not into `/Users/david/Projects`.
- Verify no entry in `sys.path` contains `/Users/david/Projects`.
- Generate an Ironclad `Identity`, sign a `KnowledgePacket`, and verify the
  `SignedPacket` round-trips (sign → verify → tamper → fail-closed).
- Run `commons world` with `COMMONS_HOME=/tmp/commons-pass5-offline/home`.
- Add a local regression script `tests/test_wheel_offline.sh`.

## Out of scope

- Committing, pushing, publishing, or registering anything.
- Modifying `pyproject.toml`, CI, README, `docs/INSTALL`, or ledger formats.
- PyPI, npm, brew, Vast, SSH, or any external registry.
- New MCP server names or dependency additions.
- Running or mutating `/tmp/commons-sim-*` or any frozen simulation home.
- `git add -A` or any bulk staging operation.
- Network access of any kind during the test phase.

## Network-isolation strategy

`uv pip install --offline --no-deps` disables all network access and installs
only the specified wheels without resolving transitive dependencies. The
aafp-commons wheel is provided via `--find-links <staged-wheels-dir>`.
Transitive dependencies (cryptography, pydantic, cbor2,
pyyaml, tomli, liboqs-python) are staged from the project venv's
site-packages into `/tmp/commons-pass5-offline/deps/` during setup, then
copied into the test venv's site-packages from `/tmp` only.

### Why `--no-deps` instead of full offline resolution

The uv cache (`~/.cache/uv/archive-v0/`) stores unpacked package archives, not
`.whl` files. `uv pip install --offline` into a fresh venv cannot resolve
transitive deps from the cache because the simple-index metadata
(`~/.cache/uv/simple-v21/`) is not populated for all packages. `--no-index`
makes this worse by blocking cache consultation entirely. The strongest
working approach is `--no-deps` for the Commons wheel (installed via
`--find-links` from `/tmp`) plus staging the already-installed transitive deps
from the project venv (the "already-cached dependencies" per the task spec).
`UV_OFFLINE=1` is the network gate — uv fails rather than contacting any
registry.

## Proving no contact with /Users/david/Projects

The test phase (everything after wheel staging) runs with:

1. `cwd=/tmp` — the process working directory is outside `/Users/david/Projects`.
2. `PYTHONPATH=` (empty) — no source-tree paths on the import path.
3. `COMMONS_HOME=/tmp/commons-pass5-offline/home` — the home directory is in `/tmp`.
4. `UV_OFFLINE=1` — uv cannot reach the network.

After install, the test asserts:

- `aafp_commons.__file__` starts with the venv site-packages prefix.
- `ironclad.__file__` starts with the venv site-packages prefix.
- No string in `sys.path` contains `/Users/david/Projects`.

### Limitation: kernel-level file-access tracing

macOS `fs_usage` / `dtruss` can trace all file-system accesses and would
provide kernel-level proof that no file under `/Users/david/Projects` is
opened. Both require `sudo` (root), which the test runner does not assume.
The test therefore provides **structural proof** at the Python import layer
(module resolution + `sys.path` audit) rather than kernel-level proof. This
is the strongest local test available without root escalation and without
mutating frozen simulation homes.

## Verification command

```bash
bash tests/test_wheel_offline.sh
```

## Acceptance

1. `tests/test_wheel_offline.sh` exits `0`.
2. The aafp-commons wheel, including vendored Ironclad, is installed from
   `/tmp/commons-pass5-offline/wheels/` with `uv pip install --offline`.
3. `aafp_commons.__file__` and `ironclad.__file__` resolve into the
   `/tmp/commons-pass5-offline/venv` site-packages.
4. No `sys.path` entry contains `/Users/david/Projects`.
5. Ironclad sign → verify → tamper → fail-closed round-trip succeeds.
6. `commons world` exits `0` with `COMMONS_HOME=/tmp/commons-pass5-offline/home`.
7. No network access occurs during the test phase (`UV_OFFLINE=1`).
8. No `/tmp/commons-sim-*` home is created or mutated.
9. No commits, no publishes, no ledger format changes, no Vast/SSH/npm/brew.
