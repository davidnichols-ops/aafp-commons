# Agent-first beta roadmap

## Available now

- Local client nodes with signed, content-addressed packets and ledgers.
- Optional Grok, Anthropic CC0, and GPT Astra 6 constitution packages.
- Runtime handshake, constitution adoption, and AAFP transport contracts.
- Explicit public snapshot export, verification, import, search, and indexing.
- Durable indexes with retained constitution metadata, limits, and structured
  machine-readable errors.
- Local authenticated publication service with privacy/authorization hooks,
  revocation, rate limits, and deterministic replication checkpoints.

## Next gates for global sharing

1. **Partially complete:** local `PublicationService` accepts verified
   snapshots and records publisher identity separately. Network deployment is
   still needed.
2. Add privacy classification and policy checks before publication, including
   organization-specific approval where required. **Packet-level policy hooks
   are now present locally; classification and organization workflows remain.**
3. **Partially complete:** authorization hooks, per-publisher limits, and
   revocation exist locally; hosted key rotation remains.
4. **Partially complete:** deterministic checkpoints and missing-ID discovery
   support resumable replication; conflict reconciliation remains.
5. Establish the public Git remote, release signing, cross-language fixtures,
   and operational response policy.

Each gate must preserve the existing invariants: local ledgers remain private
by default, only explicitly public packets leave a client, content addresses
remain stable, and optional constitutions never override provider or system
constraints.
