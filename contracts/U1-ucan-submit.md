# U1 Contract — Optional UCAN Admission on Submit

Status: implementation contract.

## Objective

Allow a submitter to attach a capability-bearing UCAN to packet admission.
The existing Ironclad packet signature, constitution resolution, policy, and
ledger remain authoritative. UCAN is an additional admission gate, not a
replacement identity, signature, constitution, or ledger format.

## Behavior

- Without `COMMONS_REQUIRE_UCAN=1`, existing local `init` and submit behavior
  remains unchanged; a missing UCAN is allowed.
- With `COMMONS_REQUIRE_UCAN=1`, `CommonsRepository.submit(..., ucan=None)`
  is rejected with the machine-readable reason `UCAN_REQUIRED`.
- A supplied UCAN is verified before a packet is written. Invalid, expired,
  not-yet-valid, incorrectly targeted, or insufficiently capable UCANs are
  rejected with a reason beginning `UCAN_INVALID`.
- `commons_propose` accepts an optional `ucan` string argument. MCP tool names
  and stdio transport remain unchanged.

## Minimal wire subset

No UCAN schema exists under `protocols/`, and no UCAN verifier exists in the
tree. U1 therefore implements the documented JWT-like subset in
`docs/VENDOR.md`, using UCAN field names and Ed25519/EdDSA. It is deliberately
not presented as full UCAN v1 interoperability.

Required payload fields are `iss`, `aud`, `sub`, `cmd`, `args`, `nonce`, and
`exp`; `nbf` is optional. The submit command is `commons/submit`, `sub` must
match the packet's `author_agent_id`, and `args.namespace` if present must
match the packet namespace. `att` must contain either the exact global
capability `{ "with": "commons://aafp-commons", "can": "commons/submit" }`
or an exact namespace capability for the packet. Non-empty `prf` is rejected
until delegation-chain verification exists.

`COMMONS_UCAN_AUDIENCE`, when set, must equal the token `aud`; otherwise a
valid non-empty `did:key` audience is accepted. Deployments should set this
value to their receiving service DID.

## Acceptance cases

Tests must prove:

1. Local submit without UCAN still passes when the environment is unset.
2. Required mode denies missing UCAN with `UCAN_REQUIRED`.
3. A valid signed UCAN with the global capability admits the packet.
4. A valid signed UCAN with an exact namespace capability admits the packet.
5. Bad signature, malformed token, expired token, wrong audience, wrong
   subject, missing capability, and non-empty proof chain are denied.
6. MCP `commons_propose` forwards a supplied UCAN and retains the frozen
   seven-tool list.
7. No network dependency or new transport is added.

## Out of scope

- OAuth, DPoP, bearer tokens, HTTP resource servers, or MCP transport changes.
- Full UCAN DAG-CBOR/CID interoperability, delegation-chain resolution,
  revocation, or UCAN invocation.
- New packet, identity, constitution, policy, or ledger formats.
