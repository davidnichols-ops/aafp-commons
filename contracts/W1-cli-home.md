# W1 Contract — `commons` CLI and Home Layout

Status: frozen 2026-09-05
Owner: local implementation
Parent: MAOS task 831, without changing its constitution/admission ownership

## Objective

Expose the existing AAFP Commons repository, ledger, policy, signing, and mesh
substrates through one local-first `commons` command with a stable home layout
and a loopback `/world` observer endpoint.

## Frozen interface

- Binary name: `commons`.
- Home directory: `$COMMONS_HOME`, falling back to `~/.commons`.
- Supported subcommands only: `(none)`, `init`, `serve`, `world`, `get`.
- `serve` binds `127.0.0.1:8081` by default and accepts `--port`.
- Before `init`, posture is `source`; world identity is absent.
- `init` creates or loads the local identity and initializes the local home
  layout. It is the explicit transition to subject posture for that key.
- `/world` and `commons world` expose these schema fields:
  `packet_set_merkle`, `local_tip`, `peer_tips`, `fork_ids`, `conflict_ids`,
  `resolution_ids`, `packet_count`, `posture`, `agent_id`, and `constitution`.
- `get` reads one packet by content address from the local object store.

The implementation must preserve immutable packet objects and the existing
ledger format. W1 does not create a second ledger, policy engine, signing
identity model, or constitution/admission model.

## Acceptance tests

1. A clean temporary `COMMONS_HOME` can run `commons` and report source
   posture without creating a signing subject.
2. `commons init` creates the home layout and reports subject posture.
3. `commons serve` listens on `127.0.0.1:8081`; `--port` selects another
   loopback port; restart does not fail because of stale address reuse.
4. `curl 127.0.0.1:<port>/world` returns valid JSON containing every frozen
   world field, including `posture`, `agent_id`, and `constitution`.
5. A two-node temporary-directory test performs one signed evidence-backed
   proposal through the existing repository path and verifies matching
   `packet_set_merkle` values without requiring matching tips.
6. `commons get <packet_id>` returns the stored signed packet and fails closed
   for an unknown or malformed content address.

## Out of scope

- MCP or `commons mcp`.
- Homebrew, npm, or release packaging.
- mDNS or public bootstrap.
- `assume_constitution` beyond the explicit initialization boundary.
- Resolution packet behavior.
- QUIC, Vast SSH, GPU evidence, or identity redesign.
- Changes to Task 831’s constitution/admission implementation.
