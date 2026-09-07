# Real-workload operating loop

Use this loop before an agent writes, reviews, or acts on a claim. It is a
local workflow for Roboflow PRs, lesson snapshots, and training-config claims;
it does not fetch evidence or change transport.

## Preflight (every session)

Use a throwaway home so the operator's real home is never touched:

```bash
export COMMONS_HOME=/tmp/commons-tx-work
commons world
commons policy show
```

Read `posture`, `packet_set_merkle`, `review_queue`, and any conflict or
resolution ids. In source posture, stop after reading: initialize only when
the operator explicitly authorizes a subject home.

## Before acting on a claim

`commons status` requires a CLAIM_ID — bare `commons status` without one
errors out. Always pass the content address:

```bash
commons status CLAIM_ID
commons get CLAIM_ID
commons rely CLAIM_ID
```

Record the status fields separately: `evidence_supplied`, `digest_checked`,
`reproduced`, `supported`, `conflict`, `rely_ok`, and `rely_reason`.

### admit != rely_ok

An admitted or signed claim is attributable, not true. Admission means the
packet passed schema and signature checks and was written to the local ledger.
`rely_ok` is a separate decision computed from verification results, conflict
state, and the active rely policy. A packet can be admitted with
`evidence_supplied: true` and still have `rely_ok: false` because no verifier
has recorded a result, the policy is in `display` mode, or an open conflict
blocks reliance.

Do not merge a PR, publish a lesson, or change a training configuration
because the claim was admitted, because `rely_ok` is absent, or because
another packet repeats the claim. Check `rely_ok` and `rely_reason` first.

## Failure paths

- If `commons status` reports a missing claim, confirm `CLAIM_ID` is a full
  `sha256:` content address from `commons query` or the imported snapshot; do
  not invent an ID or fetch a private reference.
- If the claim ID is malformed, stop and obtain the packet through the local
  `commons query`/`commons get` path. A malformed ID is not evidence that the
  claim is safe to use.
- If `rely_ok` is `false`, keep the claim in display or review state. Add or
  check the evidence bundle, run the named verification method, or escalate a
  conflict to an explicit resolution. Do not override the field by repeating
  the packet or changing the claim text.
- If `commons world` is unavailable, record the error and remain read-only;
  initialize a throwaway `COMMONS_HOME` only when the operator authorizes it.

## Offline worked example

This example imports a published snapshot, inspects a real claim, and checks
rely status — all offline, no peer connection required. The snapshot is
`published/maos-lessons-public-2026-09-05.json` (168 signed packets from MAOS).

```bash
# Run from /Users/david/Projects/aafp-commons.
# If commons is not installed, use the existing project environment:
commons() { uv run --no-sync python -m aafp_commons "$@"; }
# 1. Create a fresh throwaway directory, retaining any previous run.
export COMMONS_HOME="$(mktemp -d /tmp/commons-tx-m0-XXXXXX)"

# 2. Initialize a signing subject and install the built-in constitution
commons init

# 3. Import the published snapshot (offline — verifies every signature)
commons import-published published/maos-lessons-public-2026-09-05.json
# → {"accepted": 168}

# 4. Inspect the local world
commons world
# → posture: subject, packet_count: 168, review_queue: [...]

# 5. Pick a real claim ID from the snapshot JSON.
#    The first packet in this snapshot is:
CLAIM_ID=sha256:010709e9da8d30c8d682ff6f6030c997e69c38bdbfe009bc247680170abf32ab

# 6. Read the packet (claim text, evidence, constitution ref)
commons get "$CLAIM_ID"

# 7. Check verification status — note: status REQUIRES the claim ID
commons status "$CLAIM_ID"
# → evidence_supplied: true, digest_checked: false,
#   reproduced: false, rely_ok: false, rely_reason: "policy_display"

# 8. Evaluate the rely decision explicitly
commons rely "$CLAIM_ID"
# → display: true, consequential: false, rely_ok: false

# 9. Check the active rely policy
commons policy show
# → mode: "display", trusted_verifiers: [], accept_resolution: false
```

The claim was admitted (168 packets accepted) and carries evidence, yet
`rely_ok` is `false` because no verifier has recorded a result and the policy
is in `display` mode. This is the expected state for a freshly imported
snapshot: admission is not reliance.

## Explicit follow and pull (live replication)

Git is a snapshot, not node synchronization. To replicate between two live
Commons homes on loopback, use `follow` and `pull` explicitly:

```bash
# Terminal A — serve a home on loopback
export COMMONS_HOME=/tmp/commons-tx-peer-a
commons init
commons serve --port 8081

# Terminal B — follow the peer, then pull
export COMMONS_HOME=/tmp/commons-tx-peer-b
commons init
commons follow http://127.0.0.1:8081
commons pull
```

`follow` records the peer URL in `peers.json` (no connection is made).
`pull` connects to every followed peer, fetches `/packets`, and submits each
packet through the local admission gate. Both peers must be loopback
(`127.0.0.1` or `::1`); remote URLs are rejected.

For the offline path, use `import-published` with a snapshot file instead —
no peer or running server is required.

## Workload recipes

- **Roboflow PR:** cite the PR diff, issue, and test output as local evidence;
  claim only what the checked-out files and named tests establish. Review
  `commons status CLAIM_ID` before approving or acting.
- **Lesson snapshot:** import or propose the snapshot with its file digest and
  disclosure class; check for conflicts and resolution policy before reuse.
- **Training config:** cite the exact config/trainer files and command result;
  `supported` requires a verifier result, while `rely_ok` requires the active
  consumer policy.

## Handoff record

An agent handoff should include the home path, world JSON, claim id, status
JSON, evidence digests, and the exact command or method run. A missing bundle
is `unavailable`; readers do not resolve private paths or URLs at read time.
