# Contributing to AAFP Commons

AAFP Commons is designed for rapid agent-led iteration in a shared GitHub
workspace. Agents may work directly in the active tree and should keep each
change small, reviewable, and evidence-backed; a pull-request workflow is not
required for local iteration.

Before handing off a change:

1. Preserve the separation between AAFP identity, Ironclad signing, packet
   admission, optional constitution guidance, and derived reputation.
2. Treat constitution manifests and adoption/handshake records as immutable
   content-addressed data. Use a new version for changed content.
3. Keep optional constitutions outside authority, capability, provenance,
   reputation, and ledger admission decisions.
4. Run `make check` (or the equivalent `uv run` commands), then `make build`
   when packaging changes are involved. Use `make smoke` to exercise the
   built-in agent package setup path and `make schemas` to validate protocol
   documents.
5. Report concrete test and artifact evidence; do not claim remote transport
   behavior without a live or deterministic transport check.

For parallel instances, start with `constitutions install-all` when using the
built-in packages. For custom packages, exchange manifests with
`constitutions export` and `constitutions import-dir`, then use `agent join` to
announce runtime compatibility and request optional guidance.
