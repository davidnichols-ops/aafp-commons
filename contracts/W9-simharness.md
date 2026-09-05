# W9 Contract — Local Three-Subject Simulation Harness

Status: implementation contract; W9 remains uncommitted until the conductor
authorizes a commit.

Owner: local implementation
Parent: MAOS task 831; reuses the W1 CLI, W2 MCP, and W3 world surfaces without
changing their constitution/admission, signing, ledger, or replication
boundaries.

## Objective

Provide one in-tree script that boots three independent local Commons subjects
(A, B, C) against isolated `COMMONS_HOME` directories, drives them through the
existing CLI and MCP surfaces, prints their `/world` objects, and stops cleanly
while leaving every ledger intact. The harness is a simulation scaffold for
multi-subject behavior on a single laptop; it is not a network transport, a
benchmark, or a new protocol.

## Frozen interface

- Script path: `scripts/sim_agents.py`.
- Invocation: `uv run --no-sync python scripts/sim_agents.py` from the project
  root, or `python scripts/sim_agents.py` inside an already-synced environment.
- Homes: exactly `/tmp/commons-sim-A`, `/tmp/commons-sim-B`,
  `/tmp/commons-sim-C`. The harness must never read or write `~/.commons`.
- The harness uses only these existing surfaces:
  - `commons init` (W1) to create each subject identity and install the
    default digest-pinned constitution.
  - `commons mcp` (W2) `commons_propose` to sign and admit one evidence-backed
    packet from subject A.
  - `commons serve` (W1/W3) to expose `/world` and `/replicate` on loopback.
  - `commons world` (W1) is acceptable as a fallback read path.
- Packet namespaces proposed by the harness must live under `commons/sim/ml/`
  when packets are involved. The harness does not invent namespaces outside
  that prefix.
- The harness prints, for each subject, the full `/world` JSON object with the
  W3 frozen schema fields:
  `packet_set_merkle`, `local_tip`, `peer_tips`, `fork_ids`, `conflict_ids`,
  `resolution_ids`, `packet_count`, `posture`, `agent_id`, `constitution`.
- After the run, the harness terminates every `commons serve` process it
  started and leaves the three `/tmp/commons-sim-*` homes (identity,
  constitution, objects, ledger) on disk. It does not delete them on success.

## Behavior

1. Reset the three `/tmp/commons-sim-*` homes to a clean state at start so the
   run is reproducible. The reset removes only those three directories.
2. Run `commons init` for A, B, and C, each with its own `COMMONS_HOME`. Each
   reports `subject` posture with a distinct `agent_id`.
3. Through `commons mcp`, subject A proposes one evidence-backed packet with
   namespace `commons/sim/ml/observation`. B and C start with zero packets.
4. Start `commons serve` for A, B, and C on three distinct loopback ports
   chosen at runtime.
5. Fetch and print `/world` for each subject before replication.
6. Pull A's packet into B and C through the existing W3 `/replicate` loopback
   HTTP path. Fetch and print `/world` again for each subject.
7. Confirm all three `/world` objects share the same `packet_set_merkle` after
   replication. `local_tip` may differ because each home records its own local
   ledger authority.
8. Terminate every server process. Exit zero on success, non-zero on any
   failure, with a clear error message.

## Acceptance tests

1. `uv run --no-sync python scripts/sim_agents.py` exits zero from a clean
   `/tmp/commons-sim-*` state and prints three `/world` objects, each
   containing every W3 frozen field.
2. After the run, `/tmp/commons-sim-A`, `/tmp/commons-sim-B`, and
   `/tmp/commons-sim-C` each contain `identity.json`, `constitution.json`,
   `objects/`, and `ledger.jsonl`. No `~/.commons` directory is created or
   touched.
3. The post-replication `packet_set_merkle` values printed for A, B, and C are
   equal. A's `packet_count` is 1 before replication; B and C reach 1 after.
4. No `commons serve` process remains running after the harness exits.
5. The harness introduces no new MCP tool names, no new CLI subcommands, no
   QUIC, no Vast, no brew/npm/hatchling, no ML benchmark, no commits, no git
   staging, and no `.DS_Store`. Packet namespaces stay under `commons/sim/ml/`.
6. Existing `pytest` and `ruff check` remain clean. The harness does not touch
   W10 evidence files or W12 docs.

## Out of scope

- QUIC, mDNS, Vast SSH, GPU evidence, or any new transport.
- Brew, npm, hatchling, packaging, or release work.
- New MCP tool names, new CLI subcommands, or a second ledger format.
- ML benchmarks or model evaluation. The `commons/sim/ml/` namespace is a
  packet prefix for simulated observations, not a benchmark harness.
- Commits, git staging, or PRs. The harness is in-tree only.
- W10 evidence files, W12 docs, or any change to constitution/admission,
  signing, policy, or replication internals.
- Deletion of the `/tmp/commons-sim-*` homes on success; they are left intact
  for inspection. The harness may clean them only at the start of a run for
  reproducibility.
