# Zipper: V1-review-plane (code)

For ChatGPT / Devin. Parent commit at write time: `cf54be5`.
North star: `docs/NORTH-STAR.md`.

## Goal

Turn the review plane from docs into a local running path so an admitted
claim cannot silently become trusted. Do not build a network, hosted
publication, or AAFP UCAN daily path in this zipper.

## Invariant

`admitted ≠ digest-checked ≠ reproduced ≠ supported ≠ rely_ok`

Reads never fetch evidence. Same-operator review is not independent. A dead
reviewer leaves `in-review` with a timestamp. Constitutions stay admission
plus advisory guidance. README stays ≤ 80 lines.

## Ship

1. Queue projection: admitted claims without a terminal review are `in-review`.
2. Mechanical screens, local only (duplicate, flood, digest-lie, empty evidence,
   secret-pattern, same-operator).
3. Signed review results validating `protocols/review-result@1.schema.json`.
4. `accept-display` does not set `supported` or `rely_ok`.
5. Tests: signed false claim, fabricated evidence, unavailable evidence,
   conflicting verifiers, private ref that must not be fetched, same-operator
   second agent.

## Do not

New transport. Fetch on get/world/status. Rewrite claims. Treat the 168-lesson
snapshot as a live network.
