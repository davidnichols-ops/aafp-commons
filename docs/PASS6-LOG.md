# Commons Autonomous Pass 6

Date: 2026-09-05

## Scope

Pass 6 adds unpublished local wrapper surfaces only. The repository remains
private. No Homebrew tap push, npm publish, PyPI upload, Vast access, or W9
rerun was performed.

## T1 — Homebrew

- `Formula/commons.rb` is an in-tree formula with a private GitHub SSH `head`
  source and SSH caveats.
- The stable tarball is **BLOCKED** because no public tarball exists. The
  formula carries an RFC 2606 `.invalid` placeholder URL and an all-zero
  digest, clearly marked as non-installable.
- The formula installs the Python package and does not reimplement ledger,
  signing, policy, constitution, or packet behavior.
- Contract: `contracts/T1-brew.md`.

## T2 — npm

- `package.json` names `@aafp/commons`, sets `"private": true`, and has no
  runtime dependencies.
- `bin/commons.js` is an executable bin shim. It forwards arguments and stdio
  to `python -m aafp_commons`; it contains no Commons ledger logic.
- Contract: `contracts/T2-npm.md`.

## T3 — install documentation

- `docs/INSTALL.md` documents Homebrew and npm source installs as
  **NOT PUBLISHED — private only**.
- README remains 73 lines.
- Contract: `contracts/T3-wrappers.md`.

## Verification

- `uv run --no-sync pytest -q --ignore=tests/test_w9_simharness.py --ignore=tests/test_w11_packets.py`
  → **227 passed**.
- `uv run --no-sync ruff check .` → **All checks passed**.
- `node --check bin/commons.js` → passed.
- `python3 -m json.tool package.json` → passed.
- `ruby -c Formula/commons.rb` → `Syntax OK`.
- The shim smoke test matched `python -m aafp_commons --help` using the
  existing project virtual environment.
- Required remote-endpoint grep → clean.
- Tracked `.DS_Store` files → none.

## Commits

- `354376a` — `build: add private Homebrew formula wrapper`
- `fc2e2b7` — `build: add private npm Python shim`
- `3fe19cb` — `docs: document private wrapper sources`

This log is the final Pass 6 change and is committed separately.
