# T3 Contract — Homebrew and npm Source-Install Wrappers (Documentation Only)

Status: documentation contract; nothing is published. T3 remains uncommitted
until the conductor authorizes a commit.
Owner: local implementation
Workstream: T3-docs

## Objective

Document how a private user with read access to the private GitHub
repository can install `commons` through a Homebrew formula or an npm
package that both delegate to the Python package. The wrappers are
convenience shims: they clone or fetch the private source and run
`uv tool install` (or the equivalent `pip install` against the built
wheel). Neither wrapper is published to a public tap, the npm registry,
or PyPI. This contract only adds documentation; it does not ship a
formula file, an npm `package.json`, or any installable artifact.

## Scope

Files touched by this contract:

1. `contracts/T3-wrappers.md` — this file.
2. `docs/INSTALL.md` — extended with Homebrew and npm source-install
   sections, explicitly labeled NOT PUBLISHED / private-only.

Files explicitly not touched:

- `README.md` — remains unchanged and at or below 80 lines.
- `AGENTS.md`, `pyproject.toml`, `src/`, `tests/`, `scripts/`,
  `examples/`, `constitutions/`, `protocols/`, `v03-evidence/`.
- Any CI workflow under `.github/`.
- Any simulation home under `/tmp/commons-sim-*` or `/tmp/commons-pass*`.

## Wrapper model

Both wrappers are thin install shims that end at the same Python package
already documented in `docs/INSTALL.md` and `contracts/Q1-install.md`.
They do not reimplement the CLI, the MCP server, the ledger, signing,
constitutions, or policy.

- Homebrew wrapper: a local (unpublished) formula that depends on `uv`
  (or Python 3.11+) and runs
  `uv tool install 'aafp-commons @ git+ssh://git@github.com/davidnichols-ops/aafp-commons.git'`.
  It is loaded from a local file path or a private gist, never from a
  public tap. There is no `brew tap davidnichols-ops/...` and no
  `brew install davidnichols-ops/aafp-commons` against a public index.
- npm wrapper: a local (unpublished) `package.json` with no install or
  runtime dependencies. Its `bin` field exposes a Node shim that invokes
  `python -m aafp_commons` and forwards arguments and stdio. Install it
  from a local directory after installing the Python package from the
  private source, never from the public npm registry. There is no
  `npm install aafp-commons` against `registry.npmjs.org`.

Both wrappers require a working GitHub SSH key
(`ssh -T git@github.com` succeeds for `davidnichols-ops`) or an HTTPS
credential with private-read scope. The wrappers do not bundle a token,
do not write credentials to disk, and do not bypass the private
repository's access control.

## SSH authentication

The private repository is `git@github.com:davidnichols-ops/aafp-commons.git`
(SSH) or `https://github.com/davidnichols-ops/aafp-commons.git` (HTTPS).
For SSH, the user must have:

1. An SSH key registered with GitHub that has read access to the
   private repository.
2. A working `ssh-agent` (or `~/.ssh/config` host entry) so that
   `ssh -T git@github.com` authenticates as the GitHub user.
3. `git+ssh://git@github.com/davidnichols-ops/aafp-commons.git` resolves
   through that key. `uv` and `pip` both honor the user's SSH config.

For HTTPS, a GitHub personal access token (classic) with `repo` scope,
or a GitHub CLI (`gh auth`) credential, is required. The wrappers
document both paths but do not store tokens.

## What the documentation must NOT claim

- A public Homebrew tap (`brew install davidnichols-ops/aafp-commons`
  against a public tap).
- A public npm registry package
  (`npm install aafp-commons` against `registry.npmjs.org`).
- A PyPI release (`pip install aafp-commons` against `pypi.org`).
- That the wrappers reimplement the CLI, MCP server, ledger, or signing.
- That the wrappers work without private repository access.
- Any network endpoint other than `github.com` over SSH/HTTPS and
  loopback `127.0.0.1` for `commons serve`.

## Acceptance criteria

1. `contracts/T3-wrappers.md` exists and is scoped to documentation only.
2. `docs/INSTALL.md` contains Homebrew and npm source-install sections,
   each explicitly labeled NOT PUBLISHED / private-only, explaining SSH
   authentication and that the wrapper delegates to the Python package.
   The npm instructions match the in-tree dependency-free bin shim and do
   not claim to install Python as an npm lifecycle side effect.
3. `docs/INSTALL.md` does not claim a public tap, npm registry package,
   or PyPI release.
4. `README.md` is unchanged and remains at or below 80 lines.
5. No code, test, simulation home, CI workflow, `pyproject.toml`, or
   `examples/` path is modified.
6. No `brew install`, `brew tap`, `npm install`, `npm publish`,
   `pip install` against a registry, or `uv tool install` is executed
   by this contract.
7. No commit, stage, push, `git add -A`, or pull request is performed.

## Out of scope

- Shipping a Homebrew formula file, an npm `package.json`, or any
  installable artifact.
- Publishing to any registry (PyPI, npm, Homebrew tap).
- Modifying `pyproject.toml`, `src/`, `tests/`, CI, or the build backend.
- Touching `v03-evidence/` tunnel files or simulation homes.
- Starting processes, accessing Vast/SSH, or any remote host other than
  `github.com` for documented `git` operations.
- Committing, staging, pushing, `git add -A`, or opening a pull request.
- Rewriting history or rotating credentials.
