# Real-workload operating loop

Use this loop before an agent writes, reviews, or acts on a claim. It is a
local workflow for Roboflow PRs, lesson snapshots, and training-config claims;
it does not fetch evidence or change transport.

## Preflight (every session)

```bash
export COMMONS_HOME=/tmp/commons-work
commons world
commons policy show
```

Read `posture`, `packet_set_merkle`, `review_queue`, and any conflict or
resolution ids. In source posture, stop after reading: initialize only when
the operator explicitly authorizes a subject home.

## Before acting on a claim

```bash
commons status CLAIM_ID
commons get CLAIM_ID
```

Record the status fields separately: `evidence_supplied`, `digest_checked`,
`reproduced`, `supported`, `conflict`, `rely_ok`, and `rely_reason`. An
admitted or signed claim is attributable, not true. Do not merge a PR, publish
a lesson, or change a training configuration because `rely_ok` is absent or
because another packet repeats the claim.

## Workload recipes

- **Roboflow PR:** cite the PR diff, issue, and test output as local evidence;
  claim only what the checked-out files and named tests establish. Review
  `commons status` before approving or acting.
- **Lesson snapshot:** import or propose the snapshot with its file digest and
  disclosure class; check for conflicts and resolution policy before reuse.
- **Training config:** cite the exact config/trainer files and command result;
  `supported` requires a verifier result, while `rely_ok` requires the active
  consumer policy.

## Handoff record

An agent handoff should include the home path, world JSON, claim id, status
JSON, evidence digests, and the exact command or method run. A missing bundle
is `unavailable`; readers do not resolve private paths or URLs at read time.
