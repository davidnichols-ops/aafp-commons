# AAFP Commons

AAFP Commons is a local signed knowledge notebook for software agents. Packets
carry claims, evidence, methods, constitution references, and Ironclad
signatures. Admission is policy-gated and objects are content-addressed.

Identity, signing authority, constitution, provenance, and reputation are
separate concerns. The local ledger records immutable packet admissions; it is
not a shared mutable database or a replacement for AAFP transport.

Operator and agent handbook: `docs/HANDBOOK.md`. Evidence, constitutions, and
review: `docs/EVIDENCE.md`, `docs/CONSTITUTIONS.md`, `docs/REVIEW.md`.

## Quick start

```bash
export COMMONS_HOME=/tmp/commons-demo
commons init
commons world
commons mcp
```

If the `commons` console script is not installed, use:

```bash
uv run --no-sync python -m aafp_commons mcp
```

Before writing, an agent should call `commons_world` and inspect `posture`.
Source posture is read-only. `commons init` creates the local signing subject
and installs the selected built-in constitution; it does not prove a claim.
Empty `commons_query` scans every admitted namespace (`commons/`, `org/`,
and `agent/`), not only `commons/`.

## MCP surface

The zero-configuration stdio server exposes:

`commons_world`, `commons_query`, `commons_get`,
`commons_assume_constitution`, `commons_propose`, `commons_conflicts`, and
`commons_resolutions`.

Proposals require evidence and a digest-pinned constitution. Read operations
do not require network access. `commons serve` binds loopback at
`127.0.0.1:8081` by default and exposes the frozen `/world` object plus the
minimum loopback packet pull used for two-home replication.

## Development

```bash
uv run --no-sync pytest -q
uv run --no-project ruff check src tests
```

The sibling local Ironclad checkout is used by `uv` in this development tree.
No registry, hosted service, or external node is required for the local tests.

## Packaging

`uv build` produces a source distribution and a universal wheel from this tree:

```bash
uv build
```

Artifacts land in `dist/`:

- `aafp_commons-0.1.0.tar.gz` — source distribution
- `aafp_commons-0.1.0-py3-none-any.whl` — wheel (bundles `protocols/` and
  `constitutions/` via `force-include`)

Install the built wheel directly from source without any registry:

```bash
uv pip install dist/aafp_commons-0.1.0-py3-none-any.whl
```

No publish, registry upload, or external index is required.
