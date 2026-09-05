# Commons 0.3 Gap Audit

Audit date: 2026-09-05
Repository: `/Users/david/Projects/aafp-commons`

## 1. Tree map

| Area | Present in this tree | Evidence |
| --- | --- | --- |
| Packets and signing | Yes | `src/aafp_commons/models.py`, `signing.py`, `identity.py` |
| Ledger | Yes | `src/aafp_commons/ledger.py`, `repository.py` |
| Policy/admission | Yes | `src/aafp_commons/policy.py`, `repository.py` |
| Constitutions | Yes | `constitutions/`, `src/aafp_commons/constitutions.py`, `packages/` |
| Publication/sharing | Yes | `src/aafp_commons/publication.py`, `sharing.py`, `index.py` |
| Mesh protocol objects | Yes | `src/aafp_commons/mesh.py` |
| Mesh/world/node daemon | Partial | `commons_node.py` contains the daemon, peer replication, and `/world`; it is a top-level script, not the package CLI |
| Evidence artifacts | Present, not the install path | `v03-evidence/` contains Vast-era node logs, world blobs, and boot/tunnel scripts |

The existing `CommonsRepository` owns the current local object, constitution,
adoption, handshake, and ledger layout. W1 must reuse that ledger/policy/signing
substrate and must not introduce a second ledger format.

## 2. North-star coverage

### W1 — CLI and home layout

Missing as an integrated interface. The only packaged script is
`aafp-commons`; it has no `commons` binary, no `init`, `serve`, `world`, or
`get` subcommands, and no `$COMMONS_HOME`/`~/.commons` default. The existing
`commons_node.py` defaults to `./commons-data`, requires `--role`, binds to
`0.0.0.0`, and is not wired into the package entrypoint.

Reusable W1 substrate exists: `CommonsRepository.initialize()`, the current
`Ledger`, Ironclad identities, `commons_node.py`, and mesh models.

### W2 — MCP zero-config

Missing. There is no `commons mcp` entrypoint or MCP server/tool list in this
tree.

### W3 — world schema freeze

Partial. `commons_node.py` exposes `/world` and emits
`packet_set_merkle`, `local_tip`, `peer_tips`, `fork_ids`, `conflict_ids`,
`resolution_ids`, and `packet_count`. The current response also has `agent_id`,
`role`, and `local_height`, but does not emit the required `posture` or
`constitution` fields. No package-level `commons world` command or two-temp-dir
world fixture test exists under `tests/`.

The checked-in `v03-evidence/world-{A,B,C}.json` files prove historical mesh
observations only; they are not proof that this checkout can reproduce the
mesh without the old boot/tunnel environment.

## 3. Current CLI entrypoints

`pyproject.toml` declares exactly one script:

```toml
[project.scripts]
aafp-commons = "aafp_commons.cli:main"
```

Current `aafp-commons` subcommands are `protocols`, `demo`, `verify`,
`grokipedia`, `constitutions`, `catalog`, `agent`, `runtime`, and `sharing`.
There is no `commons` script and no W1 command group.

The separate top-level daemon is invoked as:

```text
python commons_node.py --role {publication,research,reconciliation,observer}
```

## 4. Mesh/world presence in this checkout

- `commons_node.py`: **present** in this tree.
- `src/aafp_commons/mesh.py`: **present** in this tree.
- `/world`: **present** in `commons_node.py`.
- Vast mesh results: **checked-in evidence only**; no claim is made that the
  Vast processes are currently running or that SSH tunnels are available.

## 5. Test baseline

The repository-default command was invoked:

```text
uv run pytest -q
```

It did not reach collection because the locked local dependency
`../aafp/crates/aafp-py` is absent:

```text
Failed to generate package metadata for aafp==0.1.0
Distribution not found at: /Users/david/Projects/aafp/crates/aafp-py
```

The existing repository virtual environment was then used without installing
anything:

```text
PYTHONPATH=src .venv/bin/python -m pytest -q
185 passed, 3 skipped in 0.70s
```

No test failed. The three skips are the optional local AAFP transport tests.

## 6. Verdict

**W1 can land on this tree.**

W1 should be a thin installable CLI/home/HTTP adapter over the existing
repository, ledger, policy, signing, mesh, and node code. Task 831 owns
constitution/admission behavior already present here; W1 must consume that
boundary and must not duplicate or redesign it.
