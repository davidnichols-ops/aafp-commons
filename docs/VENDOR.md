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
