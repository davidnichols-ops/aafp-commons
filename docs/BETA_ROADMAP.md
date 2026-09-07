# Agent-first beta roadmap

North star: `docs/NORTH-STAR.md`. Gates below must not violate it.

## Available now

- Local client nodes with signed, content-addressed packets and ledgers.
- Optional Grok, Anthropic CC0, and GPT Astra 6 constitution packages.
- Runtime handshake, constitution adoption, and AAFP transport contracts.
- Explicit public snapshot export, verification, import, search, and indexing.
- Durable indexes with retained constitution metadata, limits, and structured
  machine-readable errors.
- Local authenticated publication service with privacy/authorization hooks,
  revocation, rate limits, and deterministic replication checkpoints.
- Operator handbook, evidence format, custom-constitution template, and
  review-result schema (`docs/HANDBOOK.md` and related).

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
6. Run the review plane as code: visible `in-review` queue, mechanical spam
   screens, signed review results. Spec is `docs/REVIEW.md`.
7. Daily-path AAFP UCAN grants for propose, pull, and publish. Wire quality
   is not epistemic quality.

Each gate must preserve the north-star invariants: local ledgers remain private
by default, only explicitly public packets leave a client, content addresses
remain stable, optional constitutions never override provider or system
constraints, reads never fetch evidence, and import is not trust.
Now: explicit local resolution policy can permit reliance without changing support.
Trustcard gates the MCP edge; it is not part of the ledger or admission.
