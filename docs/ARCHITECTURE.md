# Architecture

## Data path

```text
agent runtime
    |
    | produces candidate + provenance
    v
KnowledgePacket --Ironclad sign--> SignedPacket
    |                                 |
    | digest-pinned constitution      | AAFP knowledge-packet capability
    v                                 v
exact manifest resolver              receiving commons node
    |                                 |
    v                                 |
mechanical admission gates <---------+
                                      |
                                      | immutable object write
                                      v
                              signed Merkle hash chain
```

## Invariants

1. AAFP identity, Ironclad signing identity, authority, constitution, and
   reputation are separate fields and separate decisions.
2. A knowledge object's content address covers the complete unsigned packet.
3. Signed packets are immutable; corrections use `supersedes` or
   `contradicts` links.
4. An admitted packet is written once and then committed to a signed block.
5. Ledger verification checks height, previous hash, Merkle root, authority
   key identity, and signature.
6. Public packets must carry evidence references and pass secret-pattern
   screening. This is an MVP guard, not a complete privacy classifier.
7. Grokipedia is research input, never an automatic truth oracle.
8. Constitution manifests are immutable at an ID/version. Packets pin the
   manifest content digest, and resolution fails closed for missing, malformed,
   or mismatched manifests.
9. A constitution constrains admission only. It does not identify an author,
   authorize a signer, establish provenance, or contribute reputation.
10. Optional guidance and source metadata on a constitution manifest are
    advisory only. They do not participate in admission decisions, grant
    authority, establish provenance, or contribute reputation. Tampering
    with them breaks the manifest digest, preserving immutability.
11. Built-in constitution packages are pre-built manifests with display
    metadata for agent discovery. Installing a package produces the same
    immutable manifest as constructing one directly — the package layer
    carries no authority.
12. Optional runtime compatibility metadata records which agent runtimes a
    constitution is known to work with. It is advisory only — it does not
    restrict admission. A runtime not listed in either `compatible` or
    `incompatible` is simply untested.
13. Optional provider constraints with explicit precedence help agents reason
    about inherited provider guidance. Precedence orders only those inherited
    constraints. Every optional manifest fixes `provider_constraint_policy` to
    `preserve`, so optional guidance cannot override provider/system rules.
14. An agent adoption request is an unsigned, content-addressed preference for
    one exact constitution manifest. It awaits runtime acceptance and is never
    evidence of identity, a capability, permission, provenance, or reputation.
    Requests live in a separate immutable store and never enter the signed
    knowledge ledger.
15. A local runtime decision may activate the exact requested guidance as
    working context. It is immutable, unsigned, request-bound, stored outside
    the ledger, and has no effect on admission, capabilities, identity,
    provenance, or reputation.
16. Constitution adoption uses a distinct optional AAFP capability and a
    content-address-checked envelope. It never reuses the signed
    `knowledge-packet` channel and carries no Ironclad authority.
17. Runtime handshakes are unsigned, content-addressed discovery metadata.
    They can advertise runtime identity conventions and accepted constitution
    digests, but never authenticate a runtime or grant it authority.

## What exists now

- local content-addressed object store;
- signed candidate packet and receipt verification;
- single-authority ledger;
- policy admission result (`admissible`, `rejected`, `already-present`);
- versioned, content-addressed constitution manifests and exact file resolver;
- constitution validation in packet admission and repository verification;
- optional agent-readable behavioral guidance and source/license metadata
  on constitution manifests (advisory only — does not participate in
  admission decisions);
- optional runtime compatibility and provider-constraint precedence metadata
  on constitution manifests (advisory only — for agent discovery and
  reasoning, not admission enforcement);
- three built-in constitution packages (`anthropic-cc0`,
  `grok-truth-seeking`, `gpt-astra-6`) with an agent-first discovery and
  selection registry;
- `ConstitutionCatalog` for agent-first discovery and selection of installed
  constitutions by runtime, namespace, packet kind, or guidance presence;
- `catalog list` and `catalog select` CLI commands for repository-level
  constitution discovery;
- bundled protocol registry and `protocols list/show` commands for agents to
  discover and retrieve every language-neutral wire schema;
- a frozen `ConstitutionAdoptionRequest` and `agent ask` CLI flow through which
  an agent explicitly asks a runtime to apply one compatible digest-pinned
  constitution as additional guidance;
- immutable local runtime decisions plus `agent respond` and `agent context`
  commands that expose guidance only after acceptance, without changing any
  authority or admission decision;
- optional AAFP transport adapter;
- optional `constitution-adoption` AAFP transport adapter with
  content-addressed request envelopes;
- runtime handshakes are a separate unsigned discovery exchange; they describe
  runtime and accepted constitution references but do not activate policy;
- runtime handshake self-description and immutable discovery storage;
- portable manifest export/import with validate-all batch preflight for parallel
  commons instances;
- unofficial Grokipedia fetch adapter.
- explicit public research snapshots, a verified read-only snapshot searcher,
  and a deduplicating durable public index suitable for later hosted migration;
  the index is discovery infrastructure, not ledger authority or consensus.
- authenticated local publication service with separate publisher attribution,
  authorization/privacy hooks, revocation, and per-publisher limits;

The `ResearchIndexBackend` interface is the local/hosted boundary. It exposes
only verified public-snapshot ingestion, bounded search, and health statistics.
`PublicResearchIndex` implements it for the beta client; a future publication
service can implement the same surface while adding authentication, publisher
identity, rate limits, revocation, and replication outside the private client
ledger.

## What remains intentionally unresolved

- AAFP UCAN wiring and namespace-specific proposal/canonicalization grants;
- distributed membership and consensus;
- canonicalization thresholds and governance;
- independence scoring across model families, prompts, and repositories;
- revocation and key rotation across both AAFP and Ironclad identities;
- centralized schema registry publication and cross-language test vectors beyond
  the repository's versioned JSON schemas;
