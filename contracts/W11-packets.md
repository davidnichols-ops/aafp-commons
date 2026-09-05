# W11 Contract — Three-Subject Evidence Packet Run

Status: implementation contract; W11 remains uncommitted until the conductor
authorizes a commit.

Owner: local implementation
Parent: MAOS task 831; reuses the W1 CLI, W2 MCP, W3 world/replication, W9
harness patterns, and W10 ML evidence index without changing their
constitution/admission, signing, ledger, or replication boundaries.

## Objective

Drive the smallest evidence-backed three-subject packet run through the
existing Commons surfaces. Subject A publishes an observation citing an exact
indexed file path and its sha256 digest from the W10 ML evidence index. Subject
B publishes a second observation that either contradicts A (only if two indexed
artifacts genuinely disagree) or supports A. Subject C emits exactly one
deterministic Resolution packet with a decision enum. The resulting signed
objects are replicated so all three worlds converge on identical
`packet_set_merkle` and exactly one identical `resolution_id`.

## Frozen interface

- Script path: `scripts/sim_packets.py`.
- Invocation: `uv run --no-sync python scripts/sim_packets.py` from the project
  root, or `python scripts/sim_packets.py` inside an already-synced environment.
- Homes: exactly `/tmp/commons-sim-A`, `/tmp/commons-sim-B`,
  `/tmp/commons-sim-C`. The script must never read or write `~/.commons`.
- The script uses only these existing surfaces:
  - `commons init` (W1) to create each subject identity and install the
    default digest-pinned constitution.
  - `commons mcp` (W2) `commons_propose` to sign and admit each packet.
  - `commons serve` (W1/W3) to expose `/world` and `/replicate` on loopback.
  - `commons world` (W1) as a fallback read path.
- Packet namespaces proposed by the script must live under `commons/sim/ml/`.
- The script prints, for each subject, the full `/world` JSON object with the
  W3 frozen schema fields, plus the three packet IDs and the resolution
  decision.
- After the run, the script terminates every `commons serve` process it
  started and leaves the three `/tmp/commons-sim-*` homes on disk.

## Resolution packet compatibility

The built-in constitutions do not admit a literal `resolution` packet kind.
W11 does not fork constitution/admission ownership or bypass policy. Instead,
C's Resolution packet is a standard `KnowledgePacket` with:

- `kind`: `finding` (an existing admissible kind).
- `namespace`: `commons/sim/ml/resolution` (under the `commons/sim/ml/`
  prefix, admitted by the existing constitution namespace scope).
- `scope`: a documented resolution payload carrying `observation_a_id`,
  `observation_b_id`, `artifact_a_digest`, `artifact_b_digest`,
  `conflict_ids`, `decision`, and `resolution_id`.
- `evidence`: two `EvidenceRef` entries citing the observation packet IDs as
  content-addressed evidence digests.
- `constitution`: the same digest-pinned constitution used by A and B.

The `resolution_id` is computed using the existing `ResolutionPacket` formula
from `src/aafp_commons/mesh.py` — `digest` over the observation IDs, artifact
digests, conflict IDs, and decision string. This is deterministic: every node
that stores the same resolution payload produces the same `resolution_id`.

## World projection

`world()` in `src/aafp_commons/w1.py` gains a minimal deterministic projection
for `conflict_ids` and `resolution_ids`. The projection scans stored packets
for namespaces `commons/sim/ml/resolution` and `commons/sim/ml/conflict` and
extracts their IDs from the packet `scope`. This does not invent a second
ledger — it reads from the same content-addressed object store. Existing
conflict IDs are preserved; the projection only adds IDs from newly admitted
packets.

## Behavior

1. Reset the three `/tmp/commons-sim-*` homes to a clean state at start.
2. Run `commons init` for A, B, and C, each with its own `COMMONS_HOME`.
3. Through `commons mcp`, subject A proposes one observation under
   `commons/sim/ml/observation` citing an exact indexed file path from the W10
   ML evidence index plus its sha256 digest.
4. Through `commons mcp`, subject B proposes a second observation under
   `commons/sim/ml/observation`. If two indexed artifacts genuinely disagree,
   B contradicts A; otherwise B publishes a support observation citing a
   different indexed artifact.
5. Through `commons mcp`, subject C proposes one Resolution packet under
   `commons/sim/ml/resolution` with `decision` exactly one of `a-preferred`,
   `b-preferred`, `both-rejected`, `incomparable`, citing the observation IDs
   and evidence digests.
6. Start `commons serve` for A, B, and C on three distinct loopback ports.
7. Replicate all packets so all three worlds have the same packet set. The
   replication uses the existing W3 `/replicate` loopback HTTP pull path.
8. Fetch and print `/world` for each subject after replication.
9. Confirm all three `/world` objects share the same `packet_set_merkle`,
   exactly one identical `resolution_id`, and preserved `conflict_ids`.
10. Terminate every server process. Exit zero on success, non-zero on failure.

## Acceptance tests

1. `uv run --no-sync python scripts/sim_packets.py` exits zero from a clean
   `/tmp/commons-sim-*` state and prints three `/world` objects, three packet
   IDs, and the resolution decision.
2. After the run, all three homes contain `identity.json`,
   `constitution.json`, `objects/`, and `ledger.jsonl`. No `~/.commons`
   directory is created or touched.
3. The post-replication `packet_set_merkle` values for A, B, and C are equal.
   Each has `packet_count` equal to 3.
4. All three `/world` objects have exactly one identical `resolution_id` in
   `resolution_ids`.
5. The resolution packet's `scope.decision` is exactly one of `a-preferred`,
   `b-preferred`, `both-rejected`, `incomparable`.
6. A's observation cites an exact file path and sha256 digest matching the W10
   ML evidence index.
7. The `world()` projection is deterministic: the same packet set always
   produces the same `conflict_ids` and `resolution_ids` lists.
8. No `commons serve` process remains running after the script exits.
9. The script introduces no new MCP tool names, no new CLI subcommands, no
   QUIC, no Vast, no brew/npm/hatchling, no new dependencies, no commits, no
   git staging, no `.DS_Store`. Packet namespaces stay under `commons/sim/ml/`.
10. Existing `pytest` and `ruff check` remain clean.

## Out of scope

- QUIC, mDNS, Vast SSH, GPU evidence, or any new transport.
- Brew, npm, hatchling, packaging, or release work.
- New MCP tool names, new CLI subcommands, or a second ledger format.
- Forking constitution/admission ownership or bypassing policy.
- ML benchmarks or model downloads. The `commons/sim/ml/` namespace is a
  packet prefix for evidence-backed observations, not a benchmark harness.
- Commits, git staging, or PRs.
- W10 evidence files or W12 docs.
- Deletion of the `/tmp/commons-sim-*` homes on success.
