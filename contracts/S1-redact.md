# S1 Contract — Tunnel Template Redaction

Status: frozen 2026-09-05
Owner: local implementation
Workstream: S1-redact

## Objective

Replace the historical `v03-evidence/tunnel-A.sh`, `tunnel-B.sh`, and
`tunnel-C.sh` files with safe local-only working-tree templates that contain
no real endpoints. The original files embedded live remote connection data;
that data must not remain in the tracked tree. Filenames are preserved.

## Frozen interface

- Three local templates remain at their original paths, but are ignored and
  untracked:
  `v03-evidence/tunnel-A.sh`, `v03-evidence/tunnel-B.sh`,
  `v03-evidence/tunnel-C.sh`.
- Each redacted template uses explicit placeholders only:
  `HOST_A`/`PORT_A`, `HOST_B`/`PORT_B`, `HOST_C`/`PORT_C` (or equivalent
  explicit `HOST`/`PORT` placeholders). No real endpoint data, credential
  strings, or live remote commands may remain.
- Templates are local loopback only: they bind `localhost` on the forwarding
  side and reference placeholders for the remote side. They are not wired to
  run against any real host.
- `examples/tunnels/README.md` states that v0.3 tunnels are local loopback
  only and that the placeholders are intentionally not configured for remote
  use.

## Acceptance criteria

1. `git ls-files` does not list the three `v03-evidence/tunnel-*.sh` paths.
2. A repository grep for forbidden endpoint fragments returns no matches in
   tracked content.
3. `examples/tunnels/README.md` exists and explains the local-loopback-only
   intent and the unconfigured placeholders.
4. No files other than this contract, the three tunnel templates, and
   `examples/tunnels/README.md` are modified.
5. No commit is created. Changes remain staged/uncommitted for operator
   review.

## Out of scope

- Modifying any other `v03-evidence/` artifacts (logs, tarballs, identities,
  boot/start scripts, world/identity JSON).
- Touching `/tmp/commons-sim-*` or starting any process.
- Vast, SSH, or any remote host access.
- Committing, pushing, or opening a pull request.
- Changes to contracts other than this one.
