# W12 Repository Public-Readiness Contract

Status: implementation contract; W12 remains uncommitted until the conductor
authorizes a commit. This contract audits the private repository for
public-readiness without publishing it.

## Objective

Prepare the AAFP Commons repository so that it can be made public without
exposing secrets, private infrastructure, or generated local state. The
contract adds a license, tightens `.gitignore`, and records audit findings.
It does not register, publish, push, or commit anything.

## Deliverables

Ship the following in-tree, without registry or dependency changes:

- `LICENSE` — Apache 2.0, suitable for a pre-release security-adjacent
  research project with a patent grant and contribution clause.
- `.gitignore` — expanded to cover `.DS_Store`, tool caches (`mypy`,
  `ruff`), build artifacts (`dist/`, `*.egg-info`), environment files
  (`.env`), simulation/evidence directories, and generated local state.
  Existing entries are preserved; no user files are deleted.
- `contracts/W12-repo-ready.md` — this file.

## Audit scope

The audit inspects git-tracked files for:

1. **Private keys** — any tracked file containing `private_key_b64`,
   `BEGIN ... PRIVATE KEY`, or equivalent key material.
2. **Remote infrastructure** — hardcoded IP addresses, SSH ports, host
   fingerprints, or tunnel endpoints in tracked scripts.
3. **Generated state** — simulation archives, object stores, node logs,
   benchmark logs, and identity files that are tracked despite `.gitignore`
   patterns (gitignore does not untrack already-tracked files).
4. **Credentials** — API keys, tokens, passwords, or `.env` content in
   tracked files.

## Out of scope

- Staging, committing, pushing, or publishing anything.
- Registering the repository on any platform.
- Touching W9 or W10 files.
- Using Vast, QUIC, brew, npm, or hatchling.
- Modifying `pyproject.toml`, dependencies, or the build backend.
- Deleting user files or existing tracked content.
- Running `git add -A` or any bulk staging operation.

## Audit findings

- `git ls-tree -r --name-only HEAD -- v03-evidence` shows no tracked
  `identity-*.json` private-key files. The ignored identity files on disk were
  not opened, staged, deleted, or rotated by W12.
- Tracked `v03-evidence/tunnel-A.sh`, `tunnel-B.sh`, and `tunnel-C.sh` expose
  remote root SSH endpoints, public IP addresses, and nonstandard SSH ports.
- Tracked boot/start/node logs and world artifacts remain historical evidence;
  `.gitignore` does not remove files already tracked by Git.
- No untracking, history rewrite, credential rotation, publication, or remote
  cleanup was performed. Those actions require a separate operator decision.

## Acceptance

- `LICENSE` exists at the repository root and contains the Apache 2.0 text.
- `.gitignore` covers `.DS_Store`, `.mypy_cache/`, `.ruff_cache/`, `dist/`,
  `*.egg-info/`, `.env`, `*.pyc`, simulation/data directories, keys, and
  generated local state. Existing entries are preserved.
- `contracts/W12-repo-ready.md` exists and documents the audit findings.
- No files are staged or committed.
- No W9/W10 files are modified.
- No new dependencies are added.
- The existing test suite remains green; Ruff remains clean.
- The audit report identifies tracked secrets, exposed infrastructure, and
  gitignore gaps with specific file paths and recommended remediation.
