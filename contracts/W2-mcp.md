# W2 Contract — Zero-Config MCP

Status: frozen 2026-09-05
Owner: local implementation
Parent: MAOS task 831; constitution/admission behavior remains owned by the
existing `constitutions.py`, `policy.py`, and `repository.py` boundaries.

## Objective

Make `commons mcp` a dependency-free stdio MCP server that works with no API
key and no required environment variable. It honors `COMMONS_HOME` when set
and exposes the local Commons world through frozen tool names.

## Frozen tools

1. `commons_world`
2. `commons_query`
3. `commons_get`
4. `commons_assume_constitution`
5. `commons_propose`
6. `commons_conflicts`
7. `commons_resolutions`

Tool descriptions must tell an agent that proposals require evidence and an
installed, digest-pinned constitution. Errors use machine-readable codes and
must not be conversational apologies.

## Protocol boundary

- Transport is stdio JSON-RPC with MCP `initialize`, `tools/list`, and
  `tools/call` handling.
- No network access, API key, MCP SDK download, or additional project.
- `COMMONS_HOME` is the only optional configuration and defaults to
  `~/.commons` through the W1 home resolver.
- Source posture is read-only. `commons_propose` and
  `commons_assume_constitution` return a structured `SOURCE_POSTURE` or
  `INIT_REQUIRED` error until the explicit `commons init` path has created a
  subject identity.
- `commons_assume_constitution` validates the already-installed constitution
  through the existing resolver; it must not create a second identity or
  bypass `commons init`.
- `commons_propose` constructs a packet, signs it with the existing Ironclad
  identity, and submits it through `CommonsRepository.submit()` and the
  existing `AdmissionPolicy`.
- Query is exact content-address lookup or bounded namespace scanning. Vector
  search is out of scope.
- Conflicts and resolutions return the existing local world collections; no
  new conflict or resolution model is introduced in W2.

## Acceptance tests

1. `commons mcp` answers `initialize` and `tools/list` over stdio.
2. `tools/list` returns exactly the seven frozen names and descriptions that
   mention evidence and constitution requirements.
3. In source posture, `commons_propose` and
   `commons_assume_constitution` return machine-readable error codes.
4. After `commons init`, an evidence-backed `commons_propose` is accepted and
   `commons_get` returns the signed packet.
5. `commons_query` and `commons_world` work with `COMMONS_HOME` set and do not
   create `~/.commons` when reading source posture.
6. Existing tests plus W2 tests pass; Ruff is clean.
7. Verification uses the existing environment only and performs no network or
   package/build-backend fetch.

## Out of scope

- Brew, npm, packaging, release work, or MCP registry publication.
- QUIC, mDNS, Vast SSH, GPU evidence, or W3 schema changes.
- New constitution, policy, identity, ledger, conflict, or resolution
  implementations.
