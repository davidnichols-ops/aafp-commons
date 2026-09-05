# Changelog

## Unreleased

- Added an authenticated publication service with separate publisher
  attribution, authorization and privacy hooks, revocation, and per-publisher
  limits.
- Added deterministic `research-checkpoint@1` artifacts and checkpoint-based
  missing-ID discovery for resumable replication.
- Added restart-safe persistence for publication indexes, publisher revocations,
  limits, and publication history.
- Added bounded `research-delta@1` export/apply and checkpoint-driven service
  synchronization for idempotent peer replication.
- Added explicit public research snapshots, verification-only exchange
  commands, deterministic snapshot search, and a durable deduplicating index
  with retained constitution metadata and resource limits.
- Added structured `research-error@1` responses and atomic snapshot-import
  preflight validation.
- Added agent-facing protocol discovery APIs and `protocols list/show` CLI
  commands, with the bundled `protocol-catalog@1` schema.
- Added `protocols show --raw` for direct schema consumption by non-Python agents.
- Added a distinct `constitution-package@1` schema for package-detail responses.
- `constitutions show` now accepts exact immutable `ID@VERSION` references.
- Added portable Anthropic CC0, Grok Truth-Seeking, and GPT Astra 6 manifests.
- Added agent-first catalog search, package verification, and atomic
  `constitutions install-all` setup.
- Added runtime handshake, adoption, join, linked working-context, and strict
  remote transport contracts.
- Added language-neutral JSON Schemas and push-based GitHub quality checks.
- Added executable join follow-up commands, guidance-aware package search, and
  distinct catalog/selection/installation response schemas.

This project iterates directly in the shared tree. Entries describe verified
capability changes; publishing and version tagging remain operator-controlled.
