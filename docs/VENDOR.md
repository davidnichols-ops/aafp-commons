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

- `iss`: Ed25519 `did:key` issuer;
- `aud`: non-empty Ed25519 `did:key` audience, optionally matched by
  `COMMONS_UCAN_AUDIENCE`;
- `sub`: packet `author_agent_id`;
- `cmd`: `commons/submit`;
- `args`: object, with optional matching `namespace` and `packet_id`;
- `nonce`, `exp`, and optional `nbf` for uniqueness and time bounds;
- `att`: an exact global or packet-namespace `commons/submit` capability;
- `prf`: must be absent or an empty list because delegation-chain resolution
  is not implemented.

`COMMONS_REQUIRE_UCAN=1` makes the UCAN mandatory for repository submission.
Without it, existing local initialization and submission remain compatible;
when a token is supplied it is always verified. The UCAN gate supplements,
and never replaces, the existing Ironclad packet signature, constitution
resolution, admission policy, or append-only ledger.
