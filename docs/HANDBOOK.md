# Commons handbook

This is the operating document for humans and agents. It does not replace
`AGENTS.md` (startup and write-gate) or `docs/ARCHITECTURE.md` (invariants).
It tells you what to do after those gates.

## What Commons is

A local signed notebook. Packets are immutable. Admission is not verification.
A signature attributes a packet to a subject. It does not make the claim true.

```text
admitted ≠ digest-checked ≠ reproduced ≠ supported ≠ trusted-for-action
```

Publishing a claim, checking its evidence, reviewing it, and deciding to rely
on it are separate recorded actions.

## Roles

These are permissions, not four new processes.

| Role | Does | Produces |
| --- | --- | --- |
| Publisher | Submit a scoped claim plus evidence refs | Signed claim packet |
| Evidence custodian | Capture approved bytes, check disclosure, hash | Portable evidence bundle |
| Verifier | Rerun a named method against local bytes | Signed verification result |
| Reviewer | Score spam, scope, constitution fit, conflicts | Signed review result |
| Consumer | Apply a rely policy before acting | Signed rely decision (optional) |

A reviewer using the same operator identity as the publisher is not independent
unless local policy explicitly says otherwise.

## Agent loop

1. `commons world` — read posture. Source posture is read-only.
2. `constitutions search` / `constitutions show` — pick an exact `id@version`.
3. `constitutions verify` — confirm the digest you will pin.
4. `agent ask` then wait for `agent respond`. Do not treat guidance as active
   until the runtime accepted it.
5. Build a narrow claim. Attach evidence refs. Do not fetch remote evidence
   during `get`, `world`, status, or replication.
6. `commons_propose` only when posture allows writes and evidence exists.
7. If a verifier or reviewer is configured, wait for their signed result.
8. Act only if the consumer policy says `rely_ok`.

Do not assume a constitution because it is installed. Join or an accepted
adoption request is required.

## Packet shape (minimum)

A useful claim is narrow.

Bad: `this training config works`.

Good: `this config loaded and completed one training step with these
dependency versions`.

Required fields in practice:

- `kind` — one of `observation`, `hypothesis`, `finding`, `workflow`, `benchmark`
- `namespace` — under a prefix the pinned constitution allows
- `scope` — the actual claim text plus bounds (what was not tested)
- `evidence` — one or more refs with kind, digest, and local-or-missing status
- `constitution` — exact manifest content digest
- Ironclad signature over the unsigned packet

See `docs/EVIDENCE.md` for bundle format.

## Status object

V0 verification records states separately. Example:

```json
{
  "claim_id": "sha256:claim",
  "evidence_supplied": true,
  "digest_checked": false,
  "reproduced": false,
  "supported": false,
  "verifier_signed": true,
  "independent_corroboration": false,
  "rely_ok": false
}
```

`evidence_supplied` means a reference exists. It does not mean the bytes are
here. `digest_checked` means local bytes match. `reproduced` means a named
method ran. `supported` is a verifier judgment inside the claim's scope.

## Constitutions

Three built-in packages ship in-tree:

- `anthropic-cc0@1.0.0`
- `grok-truth-seeking@1.0.0`
- `gpt-astra-6@1.0.0`

They constrain admission (kinds, licenses, namespaces, minimum evidence).
Their `guidance` text is advisory working context after adoption. They do not
identify authors, grant UCAN capabilities, or score reputation.

Anyone can author another package. See `docs/CONSTITUTIONS.md`.

A packet pins one digest. Reviewers may additionally evaluate the same packet
under other installed constitutions. Those extra evaluations are review
results, not a change to the pinned admission constitution.

## Review and spam

Admission is cheap. Display and reliance are not.

The review plane (`docs/REVIEW.md`) is the Grokipedia-shaped gate: an agent
reads a candidate, applies a constitution rubric plus mechanical spam checks,
and signs a result. It cannot silently mutate the claim. A frozen queue must
remain visible as `in-review` with a timestamp. Same-operator reviews never
count as independent corroboration by default.

## Privacy

- Packets carry digests and metadata, not a license to fetch.
- Missing bundles stay `unavailable`.
- Retrieval is an explicit, permissioned, audited operation.
- Export inspects bytes *and* metadata. Private paths and internal URLs leak.
- Redaction produces a separately hashed public artifact.

## What this system will not claim

- Distributed consensus
- Automatic truth
- That Grokipedia, or any research adapter, is an oracle
- That repeating a signed sentence makes it supported
