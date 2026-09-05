# Q3 Contract — `commons` Console Script Verification

Status: verified 2026-09-05; no code change required
Owner: local implementation
Parent: W1 CLI home contract (`contracts/W1-cli-home.md`)

## Objective

Verify that the `pyproject.toml` console script entry point
`commons = aafp_commons.w1:main` resolves in the built/install context and
that `commons --help` exits cleanly against a clean temporary `COMMONS_HOME`.
This is a read-only verification contract: it does not modify code, packaging,
CI, README, `docs/INSTALL`, package-data configuration, or frozen simulation
homes unless the entry point is actually missing from the install context.

## Frozen interface

- `pyproject.toml` declares under `[project.scripts]`:
  - `aafp-commons = "aafp_commons.cli:main"`
  - `commons = "aafp_commons.w1:main"`
- The `commons` entry point must resolve to `aafp_commons.w1:main`, which is
  the W1 command surface defined in `src/aafp_commons/w1.py`.
- The W1 subcommand surface exposed via `commons` is exactly:
  `(none)`, `init`, `serve`, `world`, `get`, `mcp`.
- `commons` honors `$COMMONS_HOME` for the local home directory, falling back
  to `~/.commons` when unset (per W1).

## Verification command

```bash
COMMONS_HOME=/tmp/commons-pass4-q3 uv run --no-sync commons --help
```

A fallback module-path check is also acceptable when the console script
shim is not on PATH in the active environment:

```bash
COMMONS_HOME=/tmp/commons-pass4-q3 uv run --no-sync python -m aafp_commons.w1 --help
```

## Verification result (2026-09-05)

Command: `COMMONS_HOME=/tmp/commons-pass4-q3 uv run --no-sync commons --help`

- Exit code: `0`
- stdout:
  ```
  usage: commons [-h] {init,serve,world,get,mcp} ...

  Commons is a local signed notebook other agents can replicate.

  positional arguments:
    {init,serve,world,get,mcp}
      init                create a signing subject and local home
      serve               serve the local world on loopback
      world               print the local world
      get                 read one packet by content address
      mcp                 run the zero-config stdio MCP server

  options:
    -h, --help            show this help message and exit
  ```
- stderr: a single `uv` warning that the active `VIRTUAL_ENV` does not match
  the project environment path (cosmetic; does not affect exit code or the
  resolved entry point). Also a `liboqs-python faulthandler is disabled`
  notice from an optional native dependency.

The entry point `commons = aafp_commons.w1:main` resolves correctly in the
install context. The W1 subcommand surface matches the W1 contract. No code,
packaging, CI, README, `docs/INSTALL`, package-data, or simulation-home
changes were made.

## Acceptance

1. `COMMONS_HOME=/tmp/commons-pass4-q3 uv run --no-sync commons --help`
   exits `0` and prints the W1 usage block listing exactly
   `init, serve, world, get, mcp`.
2. The `commons` entry point in `pyproject.toml` points at
   `aafp_commons.w1:main` and `src/aafp_commons/w1.py` defines
   `def main(argv: list[str] | None = None) -> int`.
3. No code change is required. If a future install context fails to expose
   the `commons` shim, the smallest scoped fix is to restore the
   `[project.scripts]` `commons` line in `pyproject.toml` or ensure
   `src/aafp_commons/w1.py` exports `main`; nothing else is in scope.

## Out of scope

- Modifying `pyproject.toml`, `src/aafp_commons/w1.py`, or any other source
  file when the entry point already resolves.
- Touching README, `docs/INSTALL`, CI workflows, package-data configuration,
  or frozen simulation homes.
- Committing, staging, pushing, or publishing anything.
- Network, PyPI, Vast, SSH, npm/brew, or new MCP server names.
- Changes to the W1 subcommand surface, world schema, or ledger format.
