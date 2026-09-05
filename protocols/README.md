# AAFP Commons protocol schemas

These versioned JSON Schemas are the language-neutral wire contract for the
agent-first constitution flow. They describe unsigned, content-addressed
preference and discovery objects only. They do not authenticate an agent,
grant authority, establish provenance, assign reputation, or override provider
or system constraints.

The Python implementation emits the same schema identifiers in its `schema`
fields and validates the content-addressed IDs before storing or transporting
objects. Consumers in Grok, Claude, Codex, JavaScript, Rust, or other runtimes
can use these files without importing the Python package.

`constitution-manifest@1.schema.json` validates the portable package documents
used by `constitutions export`, `constitutions import`, and
`constitutions import-dir`. Imported versions remain immutable; changed content
requires a new version.

Registry presentation fields such as display names and tags belong to the
optional package catalog; portable manifests deliberately carry policy,
guidance, and source metadata rather than assuming a central registry exists.

`constitution-catalog@1.schema.json` validates the machine-readable package
discovery returned by `constitutions list` and `constitutions search`, including
compatibility, scope, and source/license metadata.

`constitution-package@1.schema.json` validates the detail document returned by
`constitutions show`, including exact `ID@VERSION` inspection.
`constitution-package-error@1.schema.json` defines deterministic errors for
unknown package IDs or versions.
`protocol-error@1.schema.json` does the same for unknown protocol IDs.

`protocol-catalog@1.schema.json` validates `protocols list`, allowing an agent
to discover the exact schema IDs supported by an installed commons package.
`protocols show <id>` returns a metadata wrapper; pass `--raw` when the
consumer needs the schema document itself.
The adoption-request and runtime-handshake list commands use their dedicated
`constitution-adoption-request-list@1` and `runtime-handshake-list@1` schemas.

`research-snapshot@1` is the explicit public publication artifact;
`research-search@1` describes read-only search responses, and
`research-index@1` describes a persisted deduplicated index. Search clients
may additionally filter by namespace prefix and packet kind.
`research-stats@1` describes non-sensitive index health metrics.

`research-checkpoint@1` is a deterministic replication comparison point; it
contains sorted content IDs and a digest, never authority or consensus state.

`research-publication@1` records the authenticated publisher separately from
the packet signers contained in a public snapshot.

`publication-state@1` describes restart-safe publisher lifecycle state.

`research-delta@1` carries a bounded, signed packet delta for checkpoint-based
replication; applying the same delta twice is safe and idempotent.
Invalid exchange artifacts return `research-error@1` from the CLI.

The canonical built-in manifests are also available directly in the repository
at `../constitutions/anthropic-cc0/1.0.0.json`,
`../constitutions/grok-truth-seeking/1.0.0.json`, and
`../constitutions/gpt-astra-6/1.0.0.json`. Agents may validate and import these
portable documents with the manifest schema before starting a join.

Files:

- `constitution-adoption-request@1.schema.json`
- `constitution-adoption-decision@1.schema.json`
- `constitution-adoption-envelope@1.schema.json`
- `constitution-working-context@1.schema.json`
- `runtime-handshake@1.schema.json`
- `runtime-handshake-envelope@1.schema.json`
- `agent-join@1.schema.json`
- `constitution-manifest@1.schema.json`
- `constitution-catalog@1.schema.json`
- `constitution-package@1.schema.json`
- `constitution-package-error@1.schema.json`
- `constitution-selection@1.schema.json`
- `constitution-installation@1.schema.json`
- `protocol-catalog@1.schema.json`
- `protocol-error@1.schema.json`
- `protocol-show@1.schema.json`
- `constitution-adoption-request-list@1.schema.json`
- `runtime-handshake-list@1.schema.json`
- `research-snapshot@1.schema.json`
- `research-search@1.schema.json`
- `research-index@1.schema.json`
- `research-error@1.schema.json`
