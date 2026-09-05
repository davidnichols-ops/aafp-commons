# S3 Contract — README/AGENTS Claims Audit

Status: frozen 2026-09-05
Owner: local implementation
Workstream: S3-readme

## Objective

Audit `README.md` and `AGENTS.md` for false claims that this repository
ships any of the following, and remove or correct only those claims:

1. A Homebrew (`brew`) formula or `npm` package distribution.
2. A public mesh / shared mutable network of nodes.
3. A live Vast deployment or Vast integration.
4. A public-host deployment (anything other than loopback `127.0.0.1`).

Preserve all existing agent guidance to use MCP, evidence, and the
write-gate posture flow. Do not add dependencies, tests, or claims about
new capabilities.

## Scope

This contract touches exactly one file:

1. `contracts/S3-readme.md` — this file.

Audited (read-only) files:

- `README.md`
- `AGENTS.md`

No edits are made to `README.md` or `AGENTS.md` unless the audit finds a
false claim of the four kinds above. If no false claims are found, both
files are left untouched and the audit result is recorded here.

## Out of scope

- Modifying `tests/`, `pyproject.toml`, dependencies, or the build backend.
- Touching contracts from other workstreams (S1, S2, W*, etc.).
- Touching `v03-evidence/` tunnel files, simulation homes
  (`/tmp/commons-sim-*`), or any `examples/` paths.
- Starting processes, accessing Vast/SSH, or any remote host.
- Committing, staging, pushing, `git add -A`, or opening a pull request.
- Rewriting history or rotating credentials.

## Audit method

For each of the four claim kinds, grep `README.md` and `AGENTS.md` for
relevant keywords and read every match in context. A match counts as a
false claim only if the text asserts that the repository *has* or *ships*
that capability. Explicit denials (e.g. "No registry, hosted service, or
external node is required") and loopback-only descriptions do not count.

## Findings

### README.md

- `brew` / `npm`: no matches. The quick-start uses `uv run` and the
  `commons` console script; no package-manager distribution is claimed.
- Public mesh: no false claim. Line 9 states the local ledger "is not a
  shared mutable database or a replacement for AAFP transport." Line 51
  states "No registry, hosted service, or external node is required for
  the local tests." Both are explicit denials.
- Live Vast: no matches.
- Public-host deployment: no false claim. `commons serve` is described as
  binding loopback at `127.0.0.1:8081`; "two-home replication" is
  explicitly a loopback packet pull, not a public endpoint.

### AGENTS.md

- `brew` / `npm`: no matches.
- Public mesh: no matches.
- Live Vast: no matches.
- Public-host deployment: no matches.

## Result

No false claims of the four audited kinds are present in `README.md` or
`AGENTS.md`. Both files are left untouched.

## Acceptance criteria

1. `contracts/S3-readme.md` exists and is scoped to this audit.
2. `README.md` and `AGENTS.md` are unchanged if no false claims were found
   (the case here), or carry only removals/corrections of the four claim
   kinds if any were found.
3. No files other than this contract are modified.
4. No commit, stage, push, or `git add -A` is performed.
5. No process is started; no Vast/SSH or remote access; no
   `/tmp/commons-sim-*` mutation.
