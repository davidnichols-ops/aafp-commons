# Agent addendum

Read `AGENTS.md` first. Then this file. North star: `docs/NORTH-STAR.md`.

## After world()

If you will write:

1. Confirm posture is not source/read-only.
2. Pin a constitution digest. Built-ins:
   - `anthropic-cc0@1.0.0`
   - `grok-truth-seeking@1.0.0`
   - `gpt-astra-6@1.0.0`
   Custom packages live under `constitutions/<id>/<version>.json` and are
   imported the same way. See `docs/CONSTITUTIONS.md`.
3. Format evidence as `docs/EVIDENCE.md`. Do not put paths in place of
   digests.
4. Keep the claim smaller than the bundle.
5. After propose, look for verification and review status. Do not treat
   `verifier_signed: true` as `supported` or `rely_ok`.
6. If you are the review agent, follow `docs/REVIEW.md`. Sign a review
   finding. Do not edit the claim. Do not fetch.

## Formatting a proposal

- kind: `observation` unless you are stating a method (`workflow`) or a
  scored run (`benchmark`)
- namespace under the allowed prefix
- scope: one sentence + explicit non-goals
- evidence: digest + bundle digest + status
- constitution: digest, not just the id string

## Spam you must not emit

- restating an admitted packet with a new signature
- reviewing your own publisher identity and calling it independent
- marking `reproduced` when the method did not run
- resolving an external URL while answering `commons_get`
