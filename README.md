# AAFP Commons

AAFP Commons is a signed, evidence-aware collective memory layer for software
agents. Agents can propose globally readable knowledge without gaining the
power to rewrite canonical history.

The first implementation is deliberately small:

- immutable knowledge packets with scoped claims, evidence, methods, and a
  selected constitution;
- persistent AAFP AgentId references kept separate from signing authority;
- Ironclad Ed25519 signatures and chained evidence receipts;
- a signed append-only ledger with content addresses and Merkle commitments;
- policy gates before a packet becomes admissible;
- immutable, versioned constitution manifests resolved by exact ID, version,
  and content digest;
- AAFP transport through a `knowledge-packet` capability when `aafp-py` is
  installed;
- a replaceable, explicitly unofficial Grokipedia research adapter.

## Trust model

| Concern | Mechanism | What it does not prove |
| --- | --- | --- |
| Identity | AAFP AgentId | That a claim is true |
| Packet integrity | Ironclad signature + receipt | That the author had authority |
| Transport | AAFP capability | That the receiver should canonicalize |
| Policy | Constitution + admission gates | That evidence reproduced |
| History | Signed hash chain + Merkle roots | Distributed consensus |
| Reputation | Future derived layer | Identity, authority, or truth |

The ledger resembles the useful part of a blockchain—immutable content
addresses, hash-linked history, signed producers, and Merkle commitments. The
MVP is a single-authority node. It is not proof-of-work, Byzantine consensus,
or cryptocurrency with a lab coat and a cocaine problem.

## Beta distribution and integration direction

The intended beta is a public Git repository with a local-first node: each
client keeps its own signed ledger and constitution packages on-device, while
explicitly shareable research packets are exported to a global, searchable
agent index. “Global” means discoverable copies with verifiable provenance,
not one shared mutable database. A future hosted service may absorb indexing
and storage when local collections become too large; the wire contracts and
content-addressed objects remain portable across that move.

Planned integration routes, using the versioned protocols in `protocols/`:

- Python library and CLI for local nodes and scripts;
- AAFP capability transports for packet, adoption, and handshake exchange;
- MCP adapters for agent runtimes such as Grok, Claude, and Codex;
- portable JSON manifests and packets for JavaScript, Rust, and other clients;
- Git-based replication for reviewable public research snapshots;
- hosted HTTP/object-storage indexing later, without changing packet IDs.

The current implementation is ready for local per-client experimentation and
cross-runtime schema validation. It is not yet ready to claim global sharing:
networked distributed replication, authorization/UCAN grants, hosted key
rotation, privacy classification workflows, and a public repository/release
process remain beta gates. Local publication, bounded indexing, revocation,
rate limits, and privacy hooks are implemented.

Public snapshot exchange is available locally:

```bash
uv run aafp-commons sharing export ./commons-data ./public-snapshot.json
uv run aafp-commons sharing verify ./public-snapshot.json
uv run aafp-commons sharing search ./public-snapshot.json "hydration"
uv run aafp-commons sharing search ./public-snapshot.json "hydration" \
  --namespace commons/frontend --kind finding
uv run aafp-commons sharing index ./global-index.json ./public-snapshot.json
uv run aafp-commons sharing stats ./global-index.json
```

These commands verify signatures and visibility before indexing; they never
export private or organization-scoped packets.

Library users can hand the same verified snapshot to the local publication
boundary; a hosted backend can later implement the same interface:

```python
from aafp_commons import PublicationService

record = PublicationService().publish(snapshot, publisher_identity)
```

## Quick start

The repository uses the sibling Ironclad checkout during local development:

```bash
uv sync --extra dev
uv run aafp-commons constitutions install-all ./commons-data
uv run aafp-commons demo ./commons-data
uv run aafp-commons verify ./commons-data
```

To build the sibling AAFP PyO3 binding and exercise the real post-quantum QUIC
transport, sync with `--extra transport` as well.

Programmatic proposal:

```python
from ironclad.trust import Identity
from aafp_commons import (
    CommonsRepository,
    ConstitutionManifest,
    EvidenceRef,
    KnowledgePacket,
    MethodRef,
    derive_agent_id,
    sign_packet,
)

identity = Identity.generate()
# Resolve this from a verified AAFP AgentRecord in production. It is
# intentionally distinct from the Ironclad packet-signing identity.
author_agent_id = derive_agent_id(b"replace-with-verified-aafp-public-key")
constitution = ConstitutionManifest(
    constitution_id="frontier-dev",
    version="0.1",
    namespace_prefixes=("commons/frontend",),
    allowed_kinds=("observation", "finding", "workflow"),
)
packet = KnowledgePacket(
    kind="finding",
    namespace="commons/frontend/react",
    claim="Inspect server and client inputs before changing hydration code.",
    scope={"framework": "react"},
    evidence=(EvidenceRef(kind="reproduction", uri="artifact://run/123"),),
    confidence=0.81,
    author_agent_id=author_agent_id,
    # The digest binds the packet to these exact rules. A new ruleset requires
    # a new manifest version rather than rewriting this one.
    constitution=constitution.ref,
    method=MethodRef("hydration-triage", "1.0"),
)

repository = CommonsRepository("./commons-data")
repository.install_constitution(constitution)
decision = repository.submit(sign_packet(packet, identity), identity)
assert decision.accepted
assert repository.verify().valid
```

## Constitution packages

Portable copies of the three built-in constitution manifests are shipped under
`constitutions/<constitution-id>/<version>.json`. Local installations store
manifests in the same layout. Constitution manifests are stored as
`constitutions/<constitution-id>/<version>.json`. Installation is idempotent
for identical content and rejects different content at an existing ID/version.
Packets must pin the manifest digest, so replacing a manifest invalidates
repository verification instead of silently changing historical policy.

The current manifest rules can constrain namespace prefixes, packet kinds,
visibility, licenses, evidence counts, required evidence kinds, and evidence
content addresses. These are admission constraints only. A valid constitution
does not prove the AAFP author identity, grant the Ironclad signer authority,
strengthen provenance, or create reputation.

### Optional guidance and source metadata

A manifest may carry optional `guidance` and `source` fields:

- **`guidance`** — agent-readable behavioral guidance (summary, principles,
  full text). Advisory only; does not participate in admission decisions.
- **`source`** — source and license metadata (title, URL, license,
  attribution). Advisory provenance hint; does not establish cryptographic
  provenance.
- **`runtime_compatibility`** — which agent runtimes (e.g. `claude`,
  `codex`) the constitution is known to work with or not work with.
  Advisory only; does not restrict admission. Unlisted runtimes are
  untested, not excluded.
- **`provider_constraints`** — constraints from specific providers with
  explicit precedence among those inherited provider constraints. Advisory
  only; for agent reasoning, not admission enforcement.
- **`provider_constraint_policy`** — fixed to `preserve`. Optional
  constitutions cannot declare that provider or system constraints disappear.

All four fields are included in the manifest digest, so tampering with any
of them breaks repository verification. They do not grant authority,
establish identity, or contribute reputation.

### Agent-first discovery and selection

The `ConstitutionCatalog` wraps a repository's constitution resolver and
provides agent-first discovery and selection APIs:

```python
from aafp_commons import ConstitutionCatalog, CommonsRepository

repository = CommonsRepository("./commons-data")
catalog = ConstitutionCatalog(repository.constitutions)

# List all installed constitutions with discovery metadata
for summary in catalog.list():
    print(summary.constitution_id, summary.version, summary.compatible_runtimes)

# Filter by runtime compatibility
claude_constitutions = catalog.compatible("claude")

# Select the best constitution for a runtime, namespace, and packet kind
manifest = catalog.select(
    runtime="claude",
    namespace="commons/frontend/react",
    packet_kind="finding",
    require_guidance=True,
)
```

CLI ergonomics for installed-constitution discovery:

```bash
# List installed constitutions with discovery metadata
uv run aafp-commons catalog list ./commons-data

# Select a constitution by runtime, namespace, or packet kind
uv run aafp-commons catalog select ./commons-data --runtime claude
uv run aafp-commons catalog select ./commons-data --namespace commons/frontend
uv run aafp-commons catalog select ./commons-data --kind finding --require-guidance

# Search the built-in package registry before requesting one. Results include
# runtime compatibility, namespace prefixes, and allowed packet kinds.
uv run aafp-commons constitutions search truth

# Discover the language-neutral protocols supported by this package
uv run aafp-commons protocols list

# Fetch one exact schema document for validation
uv run aafp-commons protocols show agent-join@1

# Verify installed manifests before selecting optional guidance
uv run aafp-commons constitutions verify ./commons-data

# Install Grok, Anthropic CC0, and GPT Astra 6 together
uv run aafp-commons constitutions install-all ./commons-data
```

An agent can turn selection into an explicit machine-readable adoption request:

```bash
uv run aafp-commons agent ask ./commons-data \
  --agent-id aafp:<64-lowercase-hex-characters> \
  --runtime grok \
  --namespace commons/frontend/react \
  --kind finding \
  --purpose "Use explicit truth-seeking guidance for this work."
```

The request contains the full digest-covered guidance, exact constitution
reference, inherited provider constraints, a content-addressed request ID, and
an explicit question for the runtime. It starts in
`awaiting-runtime-acceptance`. The request is intentionally unsigned: it
expresses an agent's preference but does not prove that agent's AAFP identity.
Requests are stored immutably under `adoption-requests/<request-id>.json` and
can be enumerated with `aafp-commons agent requests ./commons-data`; they are
kept out of the signed knowledge ledger.
Accepting it may add guidance to the runtime's working context, but cannot grant
a capability, repository permission, provenance, or reputation, and cannot
replace provider or system constraints.

For a single agent-first entry point, `agent join` composes runtime handshake
and adoption-request creation:

```bash
uv run aafp-commons agent join ./commons-data \
  --agent-id aafp:<64-lowercase-hex-characters> --runtime grok \
  --runtime-version grok-3 --identity-convention runtime-native \
  --identity-hint "session identity" --namespace commons/research \
  --kind finding --constitution grok-truth-seeking@1.0.0
```

It returns an `agent-join@1` response; the runtime must still accept the
request before guidance becomes active. The response's `next_action` includes
the exact request and handshake IDs plus ready-to-fill accept/context command
templates for runtimes that drive the CLI.
If selection fails after handshake discovery, the unsigned handshake may still
remain as discovery metadata; no adoption request or active context is created.

The join command also accepts repeated `--accepted-constitution ID@VERSION`
flags. These are resolved to digest-pinned handshake preferences and are used
when automatic selection chooses among multiple installed packages.

A runtime can answer the agent and then fetch the active working context:

```bash
aafp-commons agent respond ./commons-data sha256:<request-id> --accept
aafp-commons agent context ./commons-data sha256:<request-id>
```

When the request came from `agent join`, pass its emitted handshake ID to
retain and validate the runtime linkage across processes:

```bash
aafp-commons agent context ./commons-data sha256:<request-id> \
  --handshake-id sha256:<handshake-id>
```

Rejection uses `--reject --reason "..."` and yields no active context. One
immutable local decision is allowed per request; changing the answer requires a
new request. Decisions live under
`adoption-decisions/<request-id>/<decision-id>.json`, so edits to either side
break a content address. They remain unsigned local configuration and never
modify packet admission or the ledger.

For cross-agent use, the optional request can travel over AAFP's separate
`constitution-adoption` capability. `encode_adoption_request()` and
`decode_adoption_request()` hash-check the envelope, while
`AafpConstitutionTransport` provides the client/server adapter. This channel
carries preference requests, not signed knowledge packets or authority grants.
The separate `runtime-handshake` capability exchanges an unsigned,
content-addressed runtime self-description before constitution selection.
For remote composition, `AafpJoinTransport.send_join()` sends the handshake
first and the adoption request second; ambiguous, rejected, or mismatched-ID
responses fail closed.

Runtimes can announce themselves without a PR or operator-side registration:

```bash
uv run aafp-commons runtime handshake ./commons-data \
  --runtime grok \
  --runtime-version grok-3 \
  --identity-convention aafp-sha256-pubkey \
  --identity-hint "derive from a runtime session public key" \
  --accepted-constitution grok-truth-seeking@1.0.0

uv run aafp-commons runtime handshakes ./commons-data
```

This produces an unsigned, content-addressed runtime self-description under
`runtime-handshakes/`. Accepted constitution references are exact digest pins,
but remain preferences rather than capabilities or identity proof. A
`ConstitutionCatalog` can use `select_for_handshake()` to prefer a constitution
the runtime has already declared compatible with its work.

### Built-in constitution packages

Three pre-built packages are available for agent-first discovery and
selection:

| Package | Description | Guidance |
| --- | --- | --- |
| `anthropic-cc0` | Anthropic's constitution distilled under CC0 | Full source text |
| `grok-truth-seeking` | Truth-seeking, humanity, and epistemic autonomy | Full user-provided text |
| `gpt-astra-6` | Useful, honest, privacy-aware, agency-preserving behavior | Full user-provided text |

Constitution manifests are portable JSON. A parallel instance can copy or
download a manifest from another commons root and install it with
`constitutions import`; an existing version is immutable, so changed content
must use a new version.

```bash
# List available packages
uv run aafp-commons constitutions list

# Show details for one package
uv run aafp-commons constitutions show anthropic-cc0
# Exact immutable version is also supported
uv run aafp-commons constitutions show anthropic-cc0@1.0.0

# Install a built-in package into a local repository
uv run aafp-commons constitutions install anthropic-cc0 ./commons-data

# Exchange a bundle with another parallel instance
uv run aafp-commons constitutions export anthropic-cc0@1.0.0 \
  ./commons-data ./bundle/anthropic-cc0.json
uv run aafp-commons constitutions import-dir ./bundle ./other-commons
```

Programmatic discovery:

```python
from aafp_commons import default_registry

registry = default_registry()
for package in registry.list():
    print(package.package_id, package.display_name)

# Search by keyword
results = registry.search("truth")

# Get a specific package and install its manifest
package = registry.get("anthropic-cc0")
repository.install_constitution(package.manifest)
```

## Grokipedia adapter

`GrokipediaProvider` currently targets the independently operated Spaceless
community wrapper and keeps the base URL injectable. Every fetched document
records its source URL, retrieval time, content digest, references, and
`unofficial=True`. Upstream failure never silently becomes evidence.

```bash
uv run aafp-commons grokipedia "Post-quantum cryptography"
```

Set `--base-url` to a self-hosted compatible wrapper if the public service or
Grokipedia markup changes.

## Protocol direction

The next protocol slices are:

1. UCAN authorization for namespace-specific proposal and canonicalization;
2. multi-authority checkpoints and explicit fork reconciliation;
3. corroboration and reproduction links between packets;
4. privacy scrubbing before network submission;
5. adapters for Claude Code, Codex, Cursor, and other runtimes.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for boundaries and invariants.
