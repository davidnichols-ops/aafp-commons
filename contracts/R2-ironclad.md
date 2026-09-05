# R2 Ironclad Vendoring Contract

Status: implementation contract; R2 remains uncommitted until the conductor
authorizes a commit.

Owner: local implementation
Parent: MAOS workstream R2-impl; builds on the R1 dependency audit
(`contracts/R1-ironclad.md`) which proved the project has an unresolvable
hard dependency on a private local `ironclad` v1.0.0 that is not published
to PyPI.

## Objective

Remove the path-only resolver knot (`[tool.uv.sources] ironclad = { path =
"../ironclad", editable = true }`) by vendoring the thin `ironclad.canon` /
`ironclad.trust` signing surface that `src/aafp_commons` actually consumes.
The vendored code ships inside the aafp-commons wheel, preserves the
existing `ironclad-ed25519-v1` packet format byte-for-byte, and introduces
no second signing format. No ledger JSON is rewritten. No frozen simulation
home is touched.

## Chosen path

**Minimal vendored signing surface, Ed25519 via `cryptography`, CBOR
canonical encoding via `cbor2`.**

The full `ironclad` package contains post-quantum signers (ML-DSA-65,
liboqs-python), trust-state machines, manifest signing, and hybrid
signature schemes. Commons uses none of that. The consumed surface is
exactly four symbols across two modules (per the R1 inventory):

| Symbol | Module | Purpose |
|---|---|---|
| `content_digest` | `ironclad.canon` | `sha256:` + base64url of canonical-CBOR SHA-256 |
| `Identity` | `ironclad.trust` | Ed25519 keypair: `generate()`, `from_seed()`, `sign()`, `public_bytes()`, `.key_id` |
| `Evidence` | `ironclad.trust` | Frozen dataclass: predicate, subject, timestamp, data, observer, nonce; `.digest`, `.signing_payload()` |
| `Receipt` | `ironclad.trust` | Dataclass: evidence, signature_b64, previous_receipt_digest; `.receipt_digest` |

Vendoring this surface as a top-level `ironclad` package inside the
aafp-commons wheel means **zero import changes** in `src/aafp_commons` or
`tests/` — every `from ironclad.trust import Identity` and
`from ironclad.canon import content_digest` resolves to the vendored
package after install.

## Wire format preservation

The `ironclad-ed25519-v1` packet format is defined by four deterministic
encodings. The vendored code reproduces each exactly:

### 1. `content_digest(obj)`

```
sha256:<base64url-no-pad(sha256(canonical_cbor(obj)))>
```

Where `canonical_cbor(obj) = cbor2.dumps(_sort_keys(obj), canonical=True)`.

`_sort_keys` recursively sorts dict keys, maps lists element-wise, and
normalizes floats (`-0.0` → `0.0`, strips trailing zeros via `.17g`
formatting). This is the content-addressing function used for packet IDs,
key IDs, ledger block hashes, and evidence digests.

### 2. `Evidence.signing_payload()`

```python
canonical_cbor({
    "digest": self.digest,        # content_digest of all 6 fields
    "predicate": self.predicate,
    "subject": self.subject,
})
```

Where `self.digest = content_digest({predicate, subject, timestamp, data,
observer, nonce})` — all six evidence fields.

The payload is CBOR (major type 3 map), not JSON. The Ed25519 signature
in `SignedPacket.receipt` is computed over these bytes.

### 3. `Receipt.receipt_digest`

```python
content_digest({
    "evidence": {
        "predicate": self.evidence.predicate,
        "subject": self.evidence.subject,
        "data": self.evidence.data,
        "observer": self.evidence.observer,
        "nonce": self.evidence.nonce,
    },
    "signature_b64": self.signature_b64,
    "previous_receipt_digest": self.previous_receipt_digest,
})
```

Note: the evidence sub-map excludes `timestamp`. This is the hash-chained
receipt digest that links receipts into a tamper-evident chain.

### 4. `Identity.key_id`

```python
content_digest({"ed25519_pub_b64": base64url_no_pad(public_bytes)})
```

### Nonce generation

`Evidence.nonce` defaults to `secrets.token_urlsafe(16)` — 16 random bytes
encoded as 22-character base64url without padding. When reconstructing
evidence from a stored receipt (e.g. `Evidence(**evidence_data)`), the
stored nonce is passed explicitly.

## What is vendored

```
src/ironclad/
    __init__.py     # empty namespace marker
    canon.py        # _sort_keys, canonical_cbor, canonical_json, sha256b64,
                    #   sha256hex, content_digest
    trust.py        # Identity, Evidence, Receipt
```

Total: ~120 lines of typed Python. No post-quantum code, no liboqs-python,
no trust-state machine, no manifest signing, no hybrid signatures.

## Dependencies

| Package | Role | Version constraint |
|---|---|---|
| `cbor2` | canonical CBOR encoding for content_digest + signing_payload | `>=5.0.0` |
| `cryptography` | Ed25519 key generation, signing, verification | `>=42.0.0` |

Both were already transitive dependencies of `ironclad>=1.0.0` (recorded in
`uv.lock`). They become direct dependencies of `aafp-commons`.

The `ironclad>=1.0.0` dependency and the
`ironclad = { path = "../ironclad", editable = true }` source override are
removed from `pyproject.toml`.

## pyproject.toml changes

```toml
[project]
dependencies = [
    "cbor2>=5.0.0",
    "cryptography>=42.0.0",
]

# [tool.uv.sources] — ironclad entry removed entirely

[tool.hatch.build.targets.wheel]
packages = ["src/aafp_commons", "src/ironclad"]

# [tool.mypy.overrides] — ironclad.* override removed (now vendored, type-checked)
```

## What does NOT change

- `src/aafp_commons/signing.py` — no edits; imports resolve to vendored `ironclad`
- `src/aafp_commons/ledger.py` — no edits
- `src/aafp_commons/w1.py`, `publication.py`, `index.py`, `cli.py`,
  `sharing.py`, `repository.py` — no edits
- `tests/conftest.py` and all test files — no edits; `from ironclad.trust
  import Identity` resolves to the vendored package
- Ledger JSON format (`ledger.jsonl`) — no changes
- `constitutions/` and `protocols/` — no changes
- The `ironclad-ed25519-v1` scheme string — no changes
- Existing receipts and signed packets — verify against the vendored code
  because the wire format is byte-for-byte identical

## Compatibility tests

`tests/test_r2_ironclad_compat.py` adds focused tests that:

1. **Wire-format pinning**: `content_digest`, `Evidence.signing_payload()`,
   `Evidence.digest`, and `Receipt.receipt_digest` produce byte-identical
   output to known vectors derived from the original ironclad runtime.
2. **Identity determinism**: `Identity.from_seed(<32-byte seed>)` produces
   a deterministic `key_id` and `public_bytes()` matching the original.
3. **Round-trip**: `sign_packet` → `SignedPacket.verify()` → tamper →
   fail-closed, using the vendored `ironclad.trust.Identity`.
4. **Ledger round-trip**: `Ledger.append` → `Ledger.verify()` → tamper →
   fail-closed.
5. **Receipt chain**: two receipts linked by `previous_receipt_digest`
   produce the expected `receipt_digest` chain.
6. **Float normalization**: `content_digest` with `-0.0` and `0.0` produce
   the same digest; trailing-zero floats are canonicalized.

## Out of scope

- Reading `/Users/david/Projects/ironclad` as an implementation source.
- Using a public fake `ironclad` package (PyPI `ironclad==0.1.0` is
  unrelated and does not provide `ironclad.trust` or `ironclad.canon`).
- Publishing to PyPI, npm, brew, or any registry.
- Touching frozen simulation homes (`/tmp/commons-sim-*`).
- Rewriting ledger JSON or creating a second signing format.
- Post-quantum signing, ML-DSA, liboqs-python, hybrid signatures.
- Trust-state machines, manifest signing, or any ironclad feature beyond
  the four consumed symbols.
- Commits, `git add -A`, PRs, or any git staging.
- Modifying `README.md`, `CHANGELOG.md`, `INSTALL`, CI, or docs.

## Stop conditions

Stop immediately if any plan would:
- Rewrite ledger JSON format or break existing `ledger.jsonl` parsing.
- Change the `ironclad-ed25519-v1` wire format (CBOR map structure, field
  sets, digest algorithms, or encoding).
- Require reading `/Users/david/Projects/ironclad` source code.
- Touch `/tmp/commons-sim-*` frozen simulation homes.

## Acceptance

1. `uv run pytest` passes (existing tests + new R2 compatibility tests).
2. `uv run ruff check src tests` passes.
3. `from ironclad.trust import Identity, Evidence, Receipt` and
   `from ironclad.canon import content_digest` resolve to the vendored
   `src/ironclad/` package, not `/Users/david/Projects/ironclad`.
4. `pyproject.toml` has no `ironclad` dependency and no
   `[tool.uv.sources]` ironclad entry.
5. The built wheel includes `ironclad/canon.py` and `ironclad/trust.py`.
6. No source file in `src/aafp_commons/` is modified.
7. No test file other than the new `tests/test_r2_ironclad_compat.py` is
   modified.
8. No ledger JSON, constitution JSON, or protocol schema is modified.
9. No commits, no `git add -A`, no publishes.
