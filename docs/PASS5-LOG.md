# Commons Autonomous Pass 5 Log

Status: dependency-path repair; repository remains private and nothing was
published.

## R1 reproduction

- `contracts/R1-ironclad.md` records the real path-source failure:
  `Distribution not found at: file:///private/tmp/ironclad`.
- Removing the path source exposes an unrelated public package that does not
  satisfy the required API or version. No public version was invented.

## R2 implementation

- `01e6836` vendors only the `ironclad.canon` and `ironclad.trust` surface
  already consumed by Commons, using cryptography Ed25519 and canonical CBOR.
- Existing `ironclad-ed25519-v1` packet, receipt, and ledger formats remain
  unchanged. The compatibility vectors and ledger tests pass.
- `docs/VENDOR.md` records upstream reference SHA
  `ca14e10c242908fe3ec50ee2a08ed7539eb11a14`.
- The wheel contains the vendored package and no longer needs the path-only
  Ironclad dependency.

## R3/R4

- `3e4f7d2` adds the offline wheel regression. It installs only the Commons
  wheel from `/tmp`, imports the vendored package, signs/verifies/tamper-tests
  a packet, and runs `commons world` with `UV_OFFLINE=1`.
- `f284508` documents the exact vendored-Ironclad situation in INSTALL.md;
  the dedicated explanation is six lines.

## Verification

- Offline wheel regression: PASS; network disabled and cached dependencies
  staged under `/tmp/commons-pass5-offline`.
- Permitted pytest subset: 227 passed; R2 full verification: 240 passed.
- Ruff clean; `sign_packet` imports from the isolated wheel; endpoint grep
  clean; no W9/W11 simulation rerun or mutation.
- R6 final log commit and private-origin push: pending.
