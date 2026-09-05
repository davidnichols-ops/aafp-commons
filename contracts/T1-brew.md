# T1 Homebrew Wrapper Formula Contract

Status: implementation contract; T1 remains uncommitted until the conductor
authorizes a commit. This contract adds a Homebrew wrapper formula that points
at the private git source for AAFP Commons. It does not publish, tap, or
register anything.

## Objective

Provide a local, unpublished Homebrew formula that wraps the `aafp-commons`
Python package so an operator with read access to the private GitHub
repository can install the `commons` and `aafp-commons` console scripts via
`brew install --HEAD commons`. The formula is a thin wrapper: it builds a
Homebrew-managed Python virtualenv, pip-installs the package from the cloned
source tree, and links the console scripts. It does not vendor, fork, or
replace any Python source, ledger format, constitution file, README, INSTALL
guide, test, or simulation home.

## Deliverables

Ship the following in-tree, without registry, network, or dependency changes:

- `Formula/commons.rb` — a Homebrew formula class `Commons` that:
  - declares a `head` block using Homebrew's git-capable SSH URL form
    `git@github.com:davidnichols-ops/aafp-commons.git` on branch `main`;
  - declares a `stable` block with a clearly marked placeholder URL
    (`https://example.invalid/...`, RFC 2606 reserved domain) and an
    all-zero `sha256`, because no public release tarball exists;
  - depends on `python@3.11`;
  - installs via `Language::Python::Virtualenv` by creating a virtualenv in
    `libexec` and `pip_install_and_link`-ing the buildpath source tree;
  - ships a `caveats` block explaining SSH authentication, that the formula
    is NOT published and NOT a tap, and how to set `COMMONS_HOME`;
  - ships a `test` block that invokes `commons --help` and asserts the
    output mentions `commons`.
- `contracts/T1-brew.md` — this file.

## Scope

- One new file: `Formula/commons.rb`.
- One new file: `contracts/T1-brew.md`.
- The formula references the private git remote already configured as
  `origin` (`https://github.com/davidnichols-ops/aafp-commons.git`) but uses
  the SSH git-capable form for the `head` URL.

## Out of scope

- Running `brew install`, `brew audit`, `brew test`, `brew tap-push`, or any
  network action.
- Publishing the formula to a tap, GitHub release, or any registry.
- Modifying `pyproject.toml`, `src/`, `tests/`, `README.md`, `docs/INSTALL.md`,
  ledger formats, constitution files, or any simulation home
  (`/tmp/commons-sim-*`, `docs/sim-world-*.json`).
- Adding, pinning, or fetching Python dependency resources (`cbor2`,
  `cryptography`). pip resolves transitive dependencies from PyPI at install
  time; resource pinning is a future stable-release task.
- `git add -A` or any bulk staging operation.
- Committing, pushing, or opening a pull request.

## BLOCKED: stable release tarball

Homebrew formula syntax requires a `stable` block with a `url` and `sha256`
for non-head installs. No public release tarball exists for this private
repository, and the task prohibits inventing a public URL. The stable block
therefore uses:

- `url "https://example.invalid/aafp-commons-0.1.0.tar.gz"` — a placeholder
  using the RFC 2606 reserved `.invalid` domain, clearly not a real URL.
- `sha256 "0000...0000"` — an all-zero digest that will never match a real
  download.

Stable installs (`brew install commons`) are BLOCKED and will fail by design.
Only head installs (`brew install --HEAD commons`) are supported, and only
with a working GitHub SSH key and read access to the private repository.

## SSH authentication

The `head` URL uses the git-capable SSH form
`git@github.com:davidnichols-ops/aafp-commons.git`. Homebrew clones this via
`git clone` over SSH. The operator must satisfy:

1. Read access to `github.com/davidnichols-ops/aafp-commons`.
2. A registered GitHub SSH key: `ssh -T git@github.com` must succeed.
3. The key loaded in `ssh-agent` or available via `~/.ssh/config`.

No HTTPS credential helper, token, or `GIT_ASKPASS` is configured by the
formula. SSH is the only supported transport for the head source.

## Wrapper semantics

The formula is a wrapper, not a reimplementation:

- It does not modify or vendor Python source. The installed package is the
  unmodified `aafp_commons` and `ironclad` packages from the cloned tree.
- It does not define MCP server names, ledger formats, or constitution
  content. Those ship inside the wheel via `pyproject.toml`
  `force-include` and are owned by the Python package.
- It does not replace `docs/INSTALL.md` or `README.md`. The canonical
  install instructions remain `uv tool install` and
  `python -m aafp_commons mcp`.
- The installed console scripts (`commons`, `aafp-commons`) are the entry
  points declared in `pyproject.toml` `[project.scripts]`.

## Verification (static, no network)

This contract is verified by static inspection only — no `brew` commands are
run:

1. `Formula/commons.rb` exists and defines `class Commons < Formula`.
2. The `head` URL is `git@github.com:davidnichols-ops/aafp-commons.git` with
   `branch: "main"`.
3. The `stable` URL uses `https://example.invalid/` and an all-zero sha256.
4. `caveats` mentions SSH, that the formula is not published / not a tap,
   and `COMMONS_HOME`.
5. No Python source, test, README, INSTALL, ledger, constitution, or
   simulation file is modified.
6. No commits, no staging, no network actions.

## Acceptance

- `Formula/commons.rb` is valid Ruby and parses as a Homebrew formula class.
- The formula is head-only in practice; stable is a documented BLOCKED
  placeholder.
- The caveats explain SSH authentication and the unpublished, non-tap
  status.
- No file outside `Formula/` and `contracts/` is modified.
- No `brew install`, `brew tap-push`, publish, or network action is run.
- No commits or staging occur.
