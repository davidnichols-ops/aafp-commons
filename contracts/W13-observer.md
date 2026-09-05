# W13 Contract — Read-Only World Observer Snapshots

Status: implementation contract; W13 remains uncommitted until the conductor
authorizes a commit.

Owner: local implementation
Parent: MAOS task 831; reuses the W1 CLI, W3 world surface, W9 harness, and
W11 three-subject packet run without changing their constitution/admission,
signing, ledger, or replication boundaries.

## Objective

Capture three frozen `/world` JSON snapshots — one per subject — from a clean
three-home local run of the W11 packet script, so that an external observer
can inspect the converged world state without re-running the simulation. The
observer is read-only: it curls `/world` from a running `commons serve`
process and writes the response body to disk. It does not propose packets,
does not replicate, does not sign, and does not modify any home.

## Frozen interface

- Artifact paths: `docs/sim-world-A.json`, `docs/sim-world-B.json`,
  `docs/sim-world-C.json`.
- Each artifact is the JSON object returned by `GET /world` from a
  `commons serve` process running against the corresponding
  `/tmp/commons-sim-*` home after the W11 replication cycle has converged.
  The body is pretty-printed with `indent=2, sort_keys=True` for readability;
  the field set and values are identical to the raw endpoint response.
- Each artifact contains every W3 frozen schema field:
  `packet_set_merkle`, `local_tip`, `peer_tips`, `fork_ids`,
  `conflict_ids`, `resolution_ids`, `packet_count`, `posture`,
  `agent_id`, `constitution`.
- The three artifacts share the same `packet_set_merkle` and each contains
  exactly one identical `resolution_id` in `resolution_ids`.
- `packet_count` is 3 in every artifact.
- `posture` is `subject` in every artifact.
- `agent_id` is non-null and distinct per subject (A, B, C have independent
  identities).
- `local_tip` may differ per subject because each home records its own local
  ledger authority.
- `constitution` is the same digest-pinned constitution reference in all
  three artifacts.

## Observer procedure

The observer captures snapshots from a running `commons serve` instance. The
procedure is:

1. Run `uv run --no-sync python scripts/sim_packets.py` from the project root.
   This resets `/tmp/commons-sim-A`, `/tmp/commons-sim-B`, and
   `/tmp/commons-sim-C`, boots three subjects, proposes three packets,
   replicates them over loopback HTTP, verifies convergence, terminates its
   own server processes, and leaves the three homes on disk.
2. Start one `commons serve` process per home on a distinct loopback port:
   ```bash
   COMMONS_HOME=/tmp/commons-sim-A uv run --no-sync python -m aafp_commons.w1 serve --port 18081 &
   COMMONS_HOME=/tmp/commons-sim-B uv run --no-sync python -m aafp_commons.w1 serve --port 18082 &
   COMMONS_HOME=/tmp/commons-sim-C uv run --no-sync python -m aafp_commons.w1 serve --port 18083 &
   ```
3. Wait for each server to print its bind line, then curl `/world`:
   ```bash
   curl -s http://127.0.0.1:18081/world > docs/sim-world-A.json
   curl -s http://127.0.0.1:18082/world > docs/sim-world-B.json
   curl -s http://127.0.0.1:18083/world > docs/sim-world-C.json
   ```
4. Terminate every `commons serve` process cleanly (SIGTERM or Ctrl-C). The
   homes remain on disk for inspection.

No `~/.commons` directory is created or touched. The observer uses only the
existing `commons serve` (W1/W3) `/world` HTTP endpoint. It introduces no new
CLI subcommands, no new MCP tool names, no new scripts, and no new
dependencies.

## Acceptance tests

1. `docs/sim-world-A.json`, `docs/sim-world-B.json`, and
   `docs/sim-world-C.json` exist and are valid JSON objects.
2. Each artifact contains every W3 frozen schema field. No field is missing.
3. The three artifacts share the same `packet_set_merkle` value.
4. Each artifact has `packet_count` equal to 3.
5. Each artifact has exactly one `resolution_id` in `resolution_ids`, and
   all three are identical.
6. Each artifact has `posture` equal to `subject` and a non-null `agent_id`.
7. The three `agent_id` values are distinct.
8. The three `constitution` objects share the same `constitution_id`,
   `version`, and `digest`.
9. No `commons serve` process remains running after the observer exits.
10. No `~/.commons` directory is created or touched.
11. The observer introduces no new MCP tool names, no new CLI subcommands, no
    new scripts, no new dependencies, no QUIC, no Vast, no brew/npm/hatchling,
    no model work, no commits, no git staging, and no `.DS_Store`.
12. Existing `pytest` and `ruff check` remain clean.

## Out of scope

- QUIC, mDNS, Vast SSH, GPU evidence, or any new transport.
- Brew, npm, hatchling, packaging, or release work.
- New MCP tool names, new CLI subcommands, new scripts, or a second ledger
  format.
- ML benchmarks or model evaluation.
- Commits, git staging, or PRs.
- Modifying `scripts/sim_packets.py`, `scripts/sim_agents.py`, or any source
  code under `src/`.
- Touching W10 evidence files or W12 docs.
- Proposing packets, replicating, signing, or modifying any home from the
  observer.
- Deletion of the `/tmp/commons-sim-*` homes; they are left intact for
  inspection.
