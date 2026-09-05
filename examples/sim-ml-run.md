# W11 Simulation ML Run — Replayable Three-Subject Packet Run

This document records a replayable run of `scripts/sim_packets.py` — the W11
three-subject evidence packet run. The script boots three independent Commons
subjects (A, B, C) under `/tmp/commons-sim-*`, produces an evidence-backed
observation (A), a support observation (B), and a deterministic Resolution
packet (C), then replicates all packets through the existing W3 loopback HTTP
path so all three worlds converge.

## How to replay

```bash
cd /Users/david/Projects/aafp-commons
uv run --no-sync python scripts/sim_packets.py
```

The script resets `/tmp/commons-sim-A`, `/tmp/commons-sim-B`, and
`/tmp/commons-sim-C` at start, runs the full packet cycle, and leaves the
ledgers on disk for inspection. It never touches `~/.commons`.

## Subjects and packets

| Subject | Home | Packet kind | Namespace | Role |
| --- | --- | --- | --- | --- |
| A | `/tmp/commons-sim-A` | observation | `commons/sim/ml/observation` | Primary observation citing W10 indexed artifact |
| B | `/tmp/commons-sim-B` | observation | `commons/sim/ml/observation` | Support observation citing a different W10 artifact |
| C | `/tmp/commons-sim-C` | finding | `commons/sim/ml/resolution` | Deterministic resolution packet |

## Evidence artifacts (from W10 ML evidence index)

Both observations cite real files verified during the W10 scan. Digests match
`shasum -a 256` on disk.

| Subject | Artifact path | sha256 |
| --- | --- | --- |
| A | `/Users/david/Projects/claude-yolo-v4-doc/results/summary.json` | `sha256:85f7671242a727d5b52a4ef7e16a0a808fa2265f4452663b6e2013a2ff24955d` |
| B | `/Users/david/Projects/claude-yolo-v4-doc/eval-results/Qwen--Qwen2.5-Coder-7B-Instruct_humaneval_results.json` | `sha256:90401b8e26c663a56de35ac5edea60e21306bebc68844df9ab7d4638e5725c67` |

A claims the v4 SFT+DPO pipeline achieved 88.4% HumanEval pass@1 (from
`summary.json`). B confirms the base Qwen2.5-Coder-7B-Instruct HumanEval
evaluation that established the baseline (from the base eval results JSON).
Both artifacts come from the same v4 training pipeline and do not genuinely
disagree, so B publishes a support observation.

## Resolution packet

C emits one Resolution packet with:

- **Decision**: `a-preferred` — A's claim is affirmed by B's supporting evidence.
- **resolution_id**: computed using the existing `ResolutionPacket` formula
  from `src/aafp_commons/mesh.py` — `digest` over the observation IDs, artifact
  digests, conflict IDs, and decision string. Deterministic: every node that
  stores the same resolution payload produces the same `resolution_id`.
- **kind**: `finding` (built-in constitutions do not admit a literal
  `resolution` kind; W11 uses an existing admissible kind with a documented
  resolution namespace and payload in `scope`).
- **namespace**: `commons/sim/ml/resolution` (under the `commons/sim/ml/`
  prefix, admitted by the existing constitution).
- **conflict_ids**: `[]` (no conflict in this support run).

## Replication flow

After all three subjects propose, the script starts `commons serve` on three
loopback ports and replicates through the existing W3 `/replicate` HTTP pull
path:

1. A pulls from B → A gets B's observation. A has {A, B}.
2. A pulls from C → A gets C's resolution. A has {A, B, C}.
3. B pulls from A → B gets A's observation and C's resolution. B has {A, B, C}.
4. C pulls from A → C gets A's observation and B's observation. C has {A, B, C}.

All three worlds converge on identical `packet_set_merkle` and exactly one
identical `resolution_id`.

## Representative output

Packet IDs, `local_tip`, and `resolution_id` change between runs because
identities are regenerated and `created_at` timestamps differ. The
`packet_set_merkle` also changes because it depends on the packet IDs. What is
deterministic within a run: all three subjects share the same
`packet_set_merkle`, the same `resolution_id`, and the same `conflict_ids`
after replication.

```
W11 three-subject evidence packet run: A observation, B support, C resolution
[A] init home=/tmp/commons-sim-A agent_id=aafp:0315699785aa92fc7ae326b73ae8abbc7651030b9c6bf34582fffc5b50eb5987
[B] init home=/tmp/commons-sim-B agent_id=aafp:cf82f2d0442650ddfec6d38ab07feb73ebe3a5d19dd83db51f001bb2dc64197e
[C] init home=/tmp/commons-sim-C agent_id=aafp:4ce40516fd935fed5342d339c428cfcbade9bfe2f7b2cda7696a2596c9848542
[A] proposed packet_id=sha256:b69dbe3399fac02d8d05386e9a2f29795a6ff6ce391d1415076fcf5bfd33c4ee namespace=commons/sim/ml/observation
[B] proposed packet_id=sha256:75719090f25249cb637f00d8ff3f88e43b8e278a7c8f1dfb819a97024c0946e1 namespace=commons/sim/ml/observation
[C] proposed packet_id=sha256:6b1c1d5f824ae760fd788ec1d8fbcbcda21d862f91d068c98d39a4d38a3670a2 namespace=commons/sim/ml/resolution

packet IDs:
  A observation:  sha256:b69dbe3399fac02d8d05386e9a2f29795a6ff6ce391d1415076fcf5bfd33c4ee
  B observation:  sha256:75719090f25249cb637f00d8ff3f88e43b8e278a7c8f1dfb819a97024c0946e1
  C resolution:   sha256:6b1c1d5f824ae760fd788ec1d8fbcbcda21d862f91d068c98d39a4d38a3670a2
  resolution_id:  sha256:8e27c1dca6af6bd0d7c96eb55f48dfb788d8fd67ac0195c299a02dd02b508ee9
  decision:       a-preferred

--- phase 1: /world before replication ---
[A] /world (before) packet_count=1 posture=subject resolution_ids=[] conflict_ids=[]
[B] /world (before) packet_count=1 posture=subject resolution_ids=[] conflict_ids=[]
[C] /world (before) packet_count=1 posture=subject resolution_ids=['sha256:8e27c1...'] conflict_ids=[]

--- phase 2: loopback replication ---
[A] replicate from B accepted=1 already_present=0
[A] replicate from C accepted=1 already_present=0
[B] replicate from A accepted=2 already_present=1
[C] replicate from A accepted=2 already_present=1

--- phase 3: /world after replication ---
[A] /world (after) packet_count=3 posture=subject packet_set_merkle=sha256:4accd77b... resolution_ids=['sha256:8e27c1...'] conflict_ids=[]
[B] /world (after) packet_count=3 posture=subject packet_set_merkle=sha256:4accd77b... resolution_ids=['sha256:8e27c1...'] conflict_ids=[]
[C] /world (after) packet_count=3 posture=subject packet_set_merkle=sha256:4accd77b... resolution_ids=['sha256:8e27c1...'] conflict_ids=[]

all three subjects share packet_set_merkle=sha256:4accd77b63f01be9f8ed3a7274e28bd5c00d2c0ae0e5121b217116e7b4888d00
all three subjects share resolution_id=sha256:8e27c1dca6af6bd0d7c96eb55f48dfb788d8fd67ac0195c299a02dd02b508ee9
resolution decision: a-preferred
ledgers left intact under /tmp/commons-sim-A, /tmp/commons-sim-B, /tmp/commons-sim-C
```

## World projection

The `world()` function in `src/aafp_commons/w1.py` projects `conflict_ids` and
`resolution_ids` from stored packets. The projection scans the content-addressed
object store for packets under `commons/sim/ml/resolution` and
`commons/sim/ml/conflict` namespaces and extracts their IDs from the packet
`scope`. This does not invent a second ledger — it reads from the same object
store. Existing conflict IDs are preserved.

## Observer snapshots (W13)

An observer is a read-only party that curls `/world` from a running
`commons serve` process. The W13 contract (`contracts/W13-observer.md`)
defines three frozen snapshot artifacts — `docs/sim-world-A.json`,
`docs/sim-world-B.json`, `docs/sim-world-C.json` — captured from a clean
three-home local run after replication has converged.

To capture snapshots after `sim_packets.py` has left the homes on disk:

```bash
cd /Users/david/Projects/aafp-commons

# Start one server per home on a distinct loopback port.
COMMONS_HOME=/tmp/commons-sim-A uv run --no-sync python -m aafp_commons.w1 serve --port 18081 &
COMMONS_HOME=/tmp/commons-sim-B uv run --no-sync python -m aafp_commons.w1 serve --port 18082 &
COMMONS_HOME=/tmp/commons-sim-C uv run --no-sync python -m aafp_commons.w1 serve --port 18083 &

# Wait for each server to print its bind line, then curl /world.
curl -s http://127.0.0.1:18081/world > docs/sim-world-A.json
curl -s http://127.0.0.1:18082/world > docs/sim-world-B.json
curl -s http://127.0.0.1:18083/world > docs/sim-world-C.json

# Terminate every server (SIGTERM or Ctrl-C). The homes remain on disk.
kill %1 %2 %3
```

The observer does not propose packets, replicate, sign, or modify any home.
It reads only the existing W3 `/world` HTTP endpoint. The three snapshots
share the same `packet_set_merkle` and each contains exactly one identical
`resolution_id`.

## Surfaces used

- `commons init` (W1) — create each subject identity and install the default
  digest-pinned constitution.
- `commons mcp` (W2) `commons_propose` — sign and admit each packet through
  the existing Ironclad signing, constitution, and policy path.
- `commons serve` (W1/W3) — expose `/world` and `/replicate` on loopback.
- `ResolutionPacket` from `src/aafp_commons/mesh.py` — compute the deterministic
  `resolution_id`.

No new MCP tool names, no new CLI subcommands, no new dependencies, no second
ledger, no constitution/admission fork, no QUIC, no Vast, no brew/npm/hatchling.
Packet namespaces stay under `commons/sim/ml/`.
