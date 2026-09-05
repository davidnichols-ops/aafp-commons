# S2 Ignore Contract

Status: implementation contract; S2 does not commit, push, register, or
publish anything. This contract is scoped to the S2-ignore workstream only.

## Objective

Tighten `.gitignore` so that tunnel scripts, SSH key material, and local
generated state are ignored by Git going forward, and add an offline
deterministic test that fails if forbidden remote-endpoint patterns or
the remote-root SSH login prefix (`root` + `@`) appear in git-tracked
repository content.

## Scope

This contract touches exactly three files:

1. `contracts/S2-ignore.md` — this file.
2. `.gitignore` — append new ignore patterns; preserve all existing entries.
3. `tests/test_no_remote_endpoints.py` — new guardrail test.

No other files are modified. Specifically, S2 does **not** touch:

- `v03-evidence/tunnel-*.sh` or any other tunnel / boot / start / node script.
- `README.md`, `AGENTS.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`.
- Simulation homes, world artifacts, identity files, or object stores.
- `pyproject.toml`, dependencies, or the build backend.

## Out of scope

- Untracking already-tracked files (`.gitignore` does not remove files from
  the index; untracking is a separate operator decision, see W12).
- Committing, staging, pushing, or publishing.
- Running `git add -A` or any bulk staging operation.
- Starting processes, accessing Vast/SSH, or mutating `/tmp/commons-sim-*`.
- History rewrite, credential rotation, or remote cleanup.

## .gitignore additions

The following patterns are appended to `.gitignore` (existing entries
preserved, no deletions):

- `v03-evidence/tunnel-*.sh` — tunnel scripts that expose remote SSH endpoints.
- `id_*` — SSH private key material (e.g. `id_rsa`, `id_ed25519`).
- `*.pem` — already present; kept for continuity.
- `commons-data/` — already present; kept for continuity.
- `tmp/`, `*.tmp`, `.tmp/` — safe /tmp-related patterns for local generated
  state that should never be tracked.

Note: `*.pem`, `*.key`, `keys/`, and `commons-data/` were already present
in `.gitignore` from W12. S2 does not duplicate them; it only appends the
missing patterns.

## Test design — `tests/test_no_remote_endpoints.py`

The test is a guardrail: it **fails** if forbidden endpoint patterns or
the remote-root SSH login prefix (`root` + `@`) appear in git-tracked
repository content. It is deterministic and fully offline.

### Forbidden patterns

1. The remote-root SSH login prefix (`root` + `@`).
2. `autossh` — automated SSH tunnel tool used by the tracked tunnel scripts.
3. Public IPv4 addresses with nonstandard SSH ports (`-p <port>` followed by
   a user-host pair).

### Self-safety constraint

The test source file itself is tracked repository content. To avoid the
test's own grep matching its own forbidden strings, sensitive fragments are
constructed at runtime without placing the literal forbidden strings in the
source:

- The remote-root prefix is built as `"roo" + "t" + chr(64)`.
- `autossh` is built from a character list joined at runtime.
- The IPv4 + port regex is assembled from fragments.

This ensures a clean `git grep` for the forbidden literals returns no hits
in tracked source, including the test file itself.

### Determinism

- Uses `git ls-files` to enumerate tracked files (no filesystem walk).
- Reads each tracked file as UTF-8 with `errors="replace"`.
- No network access, no subprocess beyond `git ls-files`, no time-dependent
  behavior.
- Binary files (detected by decode errors or null bytes) are skipped.

## Acceptance

- `contracts/S2-ignore.md` exists and is scoped to S2.
- `.gitignore` contains `v03-evidence/tunnel-*.sh`, `id_*`, and safe
  /tmp-related patterns. Existing entries are preserved.
- `tests/test_no_remote_endpoints.py` exists, is deterministic and offline.
- The test source contains no literal forbidden endpoint strings.
- No files are staged or committed.
- No tunnel scripts, README, AGENTS, simulation homes, or other files are
  modified beyond the three listed above.
- No processes are started; no Vast/SSH access; no `/tmp/commons-sim-*`
  mutation.

## Relationship to W12

W12 identified the tracked tunnel scripts as exposing remote root SSH
endpoints. S2 extends W12's audit by (a) ensuring future tunnel scripts are
ignored and (b) adding a test that prevents regression. S2 does not untrack
the existing tunnel scripts — that remains a separate operator decision
documented in W12.
