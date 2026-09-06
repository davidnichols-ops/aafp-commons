# V0 Contract — Verification Objects and Evidence Boundaries

Status: implementation contract.

V0 adds a local verification plane. It does not make signatures claims of
truth, add a network transport, change MCP tool names, or fetch evidence during
ordinary reads.

## Frozen objects

All objects are canonical, content-addressed, and signed with the existing
`ironclad-ed25519-v1` packet signing surface. They are admitted through the
existing repository policy path.

`EvidenceBundle` contains:

- `evidence_id`
- `claim_ids[]`
- `files[]`, each with `path_rel`, `sha256`, and either `bytes` or `absent`
- `disclosure`: `public`, `redacted`, or `private`
- optional `source_transform`
- `missing[]`

`VerificationResult` contains:

- `verification_id`, `claim_id`, `evidence_digests[]`, `method_id`
- `outcome`: `digest_checked`, `reproduced`, `supported`, `failed`, or
  `unavailable`
- `limitations[]`, `verifier_agent_id`, and `policy_id`

`RelyDecision` is local policy state. It contains `claim_id`, required status
levels, trusted verifier IDs, and `allow_same_operator` (false by default).

## Status semantics

The four displayed fields remain separate: `evidence_supplied`,
`digest_checked`, `reproduced`, and `supported`. An admitted claim may have all
four false except for evidence supplied. Repeated copies do not upgrade status.

- `evidence_supplied`: bytes or a locator was recorded.
- `digest_checked`: supplied bytes match the declared SHA-256 digest.
- `reproduced`: the named method ran and its outcome was recorded.
- `supported`: a verifier judged the evidence supports this claim in scope.
- `unavailable`: the bundle is not local; reads never fetch it.
- `redacted`: the public artifact has a different digest from its private source.

## Commands

The CLI adds:

```text
commons evidence pack CLAIM_ID --out BUNDLE.json
commons evidence check BUNDLE.json
commons verify CLAIM_ID --method METHOD_ID
commons status CLAIM_ID
```

`commons evidence pack` records local files and hashes them. `check` verifies
local bundle bytes without network access. `verify` records a local
`VerificationResult` with `unavailable` until a named method implementation
actually runs and returns an outcome; it never claims support from recording
the method name alone. `status` prints the four
status fields independently.

## Boundaries and acceptance

- A signed false claim can be admitted but is not supported by admission alone.
- Fabricated or changed evidence fails digest checking.
- Missing bundles report unavailable and do not trigger network reads.
- Conflicting verification results remain append-only and can be cited by an
  existing resolution packet.
- Private paths and URLs are rejected from public export unless a redacted
  artifact has its own digest and a transform record.
- A verifier using the same operator identity as the publisher is not counted
  as independent corroboration when `allow_same_operator` is false.
- No `~/.commons` writes, network fetches, new MCP tools, OAuth, DPoP, or
  transport discovery are added by V0.
