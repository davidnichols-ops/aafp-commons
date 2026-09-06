# U1 Contract — Optional UCAN Admission on Submit

Status: implementation contract, tightened after the self-issued grant bypass.

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

No UCAN schema or verifier existed under `protocols/` when U1 was added.
U1 therefore implements the documented JWT-like subset in
`docs/VENDOR.md`, using UCAN field names and Ed25519/EdDSA. It is deliberately
not presented as full UCAN v1 interoperability.

Required payload fields are `iss`, `aud`, `sub`, `cmd`, `args`, `nonce`, `att`, and
`exp`; `nbf` is optional. The submit command is `commons/submit`, `sub` must
match the packet's `author_agent_id`, and `args.namespace` if present must
match the packet namespace. `att` must contain either the exact global
capability `{ "with": "commons://aafp-commons", "can": "commons/submit" }`
or an exact namespace capability for the packet. Non-empty `prf` is rejected
until delegation-chain verification exists.

## Operator trust boundary

Every supplied token requires a configured `COMMONS_UCAN_AUDIENCE` equal to
its `aud` and `COMMONS_UCAN_TRUSTED_ISSUERS`, a JSON map from issuer Ed25519
DIDs to lists of allowed resource strings. Missing, empty, or malformed trust
configuration denies admission. A cryptographically valid self-issued grant
never creates trust. Trust comes only from the receiving process configuration,
not from packet fields, a constitution, MCP arguments, or the token itself.

Resources are exact `commons://namespace/<packet.namespace>` strings, or the
explicit whole-service grant `commons://aafp-commons`. No prefixes or wildcards
are inferred. Every `att` entry must be within the issuer's configured grants,
and at least one must cover the submitted packet. Namespace-only trust cannot
grant whole-service authority. Unknown capability caveats are rejected.
Unknown payload or argument fields, duplicate JSON fields, and non-finite JSON
values also reject. Wire tokens use unpadded canonical base64url and are limited
to 16,384 characters. Unsupported restrictions must not be silently ignored.

`args.signer_key_id` is required and must equal the verified Ironclad packet
signer's key ID. This binds the permission to the signer while preserving the
separate author identity (`sub`). The verifier accepts a trusted
`signer_key_id` argument; the admission policy supplies it from `SignedPacket`.
It also accepts explicit `trusted_issuers` and `expected_audience` keyword
arguments for embedding applications; explicit empty values deny, never fall
back to environment configuration. `commons init` does not auto-trust anyone.

The token is a reusable, expiring grant. Its nonce is not replay protection;
identical signed packets retain existing idempotent submission behavior.
Proof chains and revocation protocols remain outside this subset.

## Acceptance cases

Tests must prove:

1. Local submit without UCAN still passes when the environment is unset.
2. Required mode denies missing UCAN with `UCAN_REQUIRED`.
3. A valid signed UCAN from an explicitly trusted global issuer admits the packet.
4. A valid signed UCAN from an issuer trusted for that exact namespace admits it.
5. Bad signature, malformed token, expired token, wrong audience, wrong
   subject, missing capability, and non-empty proof chain are denied.
6. MCP `commons_propose` forwards a supplied UCAN and retains the frozen
   seven-tool list.
7. No network dependency or new transport is added.
8. Self-issued grants, absent trust, widened grants, signer substitution, and
   missing audience configuration are denied without writing objects or ledger.
9. Local initialization and source reads work with required mode enabled;
   removing configured issuer trust affects subsequent submissions immediately.

## Out of scope

- OAuth, DPoP, bearer tokens, HTTP resource servers, or MCP transport changes.
- Full UCAN DAG-CBOR/CID interoperability, delegation-chain resolution,
  revocation, or UCAN invocation.
- New packet, identity, constitution, policy, or ledger formats.

## Trust-boundary regression evidence (2026-09-05)

Before the fix, the first six trust regressions produced **5 failed, 1 passed**:
untrusted issuers, missing trust/audience, widened grants, and substituted signers
were accepted. After the fix, the permitted suite produced **286 passed** using
`uv run --no-sync pytest -q --ignore=tests/test_w9_simharness.py --ignore=tests/test_w11_packets.py`
with inherited `COMMONS_REQUIRE_UCAN`, `COMMONS_UCAN_AUDIENCE`, and
`COMMONS_UCAN_TRUSTED_ISSUERS` unset and loopback access permitted.
The frozen W9/W11 simulations were not rerun. `uv run --no-sync ruff check src
tests examples` and `git diff --check` passed. MCP's frozen tool-list test,
the endpoint guard, and signing compatibility vectors are included in the suite.
