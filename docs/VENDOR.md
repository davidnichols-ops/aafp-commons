# Vendored signing surface

Commons vendors only the thin `ironclad.canon` and `ironclad.trust` surface
needed by its existing packet signing code. It preserves the
`ironclad-ed25519-v1` CBOR/Ed25519 wire format; it is not a second ledger or
signing format.

Compatibility reference:

- Upstream project: local Ironclad v1.0.0 reference tree
- Upstream commit: `ca14e10c242908fe3ec50ee2a08ed7539eb11a14`
- Vendored scope: `src/ironclad/canon.py` and `src/ironclad/trust.py`
- Verification: `tests/test_r2_ironclad_compat.py` pins digest, evidence,
  receipt, identity, packet, and ledger compatibility vectors.

The full upstream tree is intentionally not copied; Commons uses no
post-quantum, transport, or trust-state modules from it.

## Minimal UCAN admission subset

No UCAN schema or verifier existed under `protocols/` when optional UCAN
admission was added. Commons therefore implements a deliberately bounded,
JWT-like subset using existing `cryptography` Ed25519 support; no network or
new verification dependency is added. It is not full UCAN v1 interoperability.

The compact token is `base64url(header).base64url(payload).base64url(signature)`.
The header is exactly `{"alg":"EdDSA","typ":"JWT"}` and the signature is
Ed25519 over the two encoded segments. The payload reuses UCAN names:

- `iss`: Ed25519 `did:key` issuer explicitly trusted by the receiving operator;
- `aud`: Ed25519 `did:key` audience, required to match the configured
  `COMMONS_UCAN_AUDIENCE`;
- `sub`: packet `author_agent_id`;
- `cmd`: `commons/submit`;
- `args`: object with required `signer_key_id` matching the verified Ironclad
  packet signer, and optional matching `namespace` and `packet_id`;
- `nonce`: non-empty token identifier, not a replay-prevention mechanism;
- `exp` and optional `nbf`: integer time bounds;
- `att`: exact global or namespace `commons/submit` capabilities, all within
  the issuer's configured authority and at least one covering the packet;
- `prf`: must be absent or an empty list because delegation-chain resolution
  is not implemented.

`COMMONS_REQUIRE_UCAN=1` makes the UCAN mandatory for repository submission.
Without it, existing local initialization and submission remain compatible;
when a token is supplied it is always verified. The UCAN gate supplements,
and never replaces, the existing Ironclad packet signature, constitution
resolution, admission policy, or append-only ledger.

### Operator trust configuration

Signature verification proves who signed a token, not their authority to grant
access. The receiver must configure both its audience and an issuer-to-resource
map, independently of the submitted packet and token. For example (replace the
placeholders with real Ed25519 `did:key` values):

```sh
export COMMONS_UCAN_AUDIENCE='did:key:z<receiver-public-key>'
export COMMONS_UCAN_TRUSTED_ISSUERS='{"did:key:z<issuer-public-key>":["commons://namespace/commons/research"]}'
export COMMONS_REQUIRE_UCAN=1
```

Only `commons://aafp-commons` explicitly grants whole-service authority. Namespace
resources match exactly; prefixes and wildcards have no inferred meaning. A
namespace-trusted issuer cannot issue a global grant. Missing, empty, malformed,
or untrusted issuer configuration rejects supplied tokens with `UCAN_INVALID`.
The same applies to absent or mismatched audience configuration. Initialization
does not automatically trust any issuer or create extra keys.

Embedding callers may pass `trusted_issuers`, `expected_audience`, and the
**verified** packet's `signer_key_id` to `verify_ucan`. Explicit empty trust or
audience values deny; they do not fall back to the environment. Admission policy
supplies the signer from `SignedPacket`, preserving the separate AAFP author ID.
Previously issued tokens without signer binding must be reissued, and the
receiver must configure trust; existing packet signatures and ledgers are unchanged.

This subset rejects unknown token fields, argument constraints, and capability
caveats, rather than silently ignoring restrictions. Tokens are limited to 16,384
characters, use unpadded canonical base64url, and reject duplicate JSON fields
and non-finite JSON values. Tokens are reusable until expiry: a nonce is not a
one-shot invocation. Identical signed packets retain idempotent admission.
Removing issuer trust blocks later submissions but does not invalidate ledger
history. Delegation chains, distributed revocation, and full UCAN interoperability
remain unimplemented; this is not authorization for a hosted HTTP service.
