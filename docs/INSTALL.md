# Install from the private repository

These commands require read access to the private GitHub repository and a
working GitHub SSH key or HTTPS credential.

## uv tool

SSH:

```bash
uv tool install 'aafp-commons @ git+ssh://git\@github.com/davidnichols-ops/aafp-commons.git'
```

HTTPS:

```bash
uv tool install 'aafp-commons @ git+https://github.com/davidnichols-ops/aafp-commons.git'
```

The installed console script is `commons`. The module invocation is also
supported:

```bash
python -m aafp_commons mcp
```

For local checks, use an isolated home and never the default user home:

```bash
COMMONS_HOME=/tmp/commons-pass4-install commons world
```

The wheel carries the built-in constitution JSON files, including
`grok-truth-seeking@1.0.0`; it does not read David's development checkout.

## Ironclad dependency

The wheel vendors the thin `ironclad.canon` and `ironclad.trust` surface used
by Commons. It does not resolve the unrelated public `ironclad` package or a
development-tree path; Ed25519/CBOR compatibility is tested in-tree.

## Optional AAFP transport

The default install does not build the Rust-backed AAFP transport. To enable
it, use the reproducibly pinned public source:

```bash
uv sync --extra transport
```

This fetches `davidnichols-ops/aafp` at the commit recorded in `pyproject.toml`
and `uv.lock`, using the `crates/aafp-py` subdirectory. A Rust toolchain is
required only for this optional extra.

## SSH authentication

Both wrapper sections below assume you can reach the private repository over
SSH. Verify before installing:

```bash
ssh -T git@github.com
```

You should see `Hi davidnichols-ops! You've successfully authenticated...`.
Requirements:

1. An SSH key registered with GitHub that has read access to the private
   repository.
2. A running `ssh-agent` (or a `~/.ssh/config` host entry) so that
   `ssh -T git@github.com` authenticates as the GitHub user.
3. `git+ssh://git@github.com/davidnichols-ops/aafp-commons.git` resolves
   through that key. `uv` and `pip` both honor the user's SSH config.

For HTTPS instead, a GitHub personal access token (classic) with `repo`
scope, or a `gh auth` credential, is required. The wrappers do not store
tokens.

## Homebrew wrapper (NOT PUBLISHED — private only)

There is no public Homebrew tap. The in-tree formula is a local, unpublished
wrapper around the Python package. From a checkout with private-repository
access, load the formula by path — never from a public tap:

```bash
brew install --formula ./Formula/commons.rb
```

For this private repository, use the formula's `--HEAD` path install so
Homebrew clones the SSH source; the stable tarball is deliberately blocked:

```bash
brew install --HEAD --formula ./Formula/commons.rb
```

This is a convenience shim. It does not reimplement the CLI, the MCP
server, the ledger, signing, constitutions, or policy — it installs the
Python package and exposes the `commons` console script. There is no
`brew tap davidnichols-ops/...` and no
`brew install davidnichols-ops/aafp-commons` against a public index.

## npm wrapper (NOT PUBLISHED — private only)

There is no public npm registry package. The in-tree, unpublished
`package.json` is a bin shim: it delegates each invocation to
`python -m aafp_commons`. Install the private source locally (after the
Python package is installed in the interpreter on `PATH`) — never from
`registry.npmjs.org`:

```bash
npm install --global /path/to/aafp-commons
# or, after cloning the private repository:
npm install --global .
```

The package has no install or runtime dependencies. Its `bin` field exposes
the Node shim, which forwards arguments and stdio to the Python module:

```json
{
  "name": "@aafp/commons",
  "version": "0.1.0",
  "private": true,
  "bin": { "commons": "bin/commons.js" }
}
```

This is a convenience shim. It does not reimplement the CLI, the MCP
server, the ledger, signing, constitutions, or policy. Install the Python
package separately using the private `uv tool install` command above; then
the shim invokes that installed package. There is no `npm install
aafp-commons` against `registry.npmjs.org` and no PyPI release.

## What the wrappers are not

- No public Homebrew tap, no public npm registry package, no PyPI release.
- The wrappers do not bundle credentials or bypass the private
  repository's access control.
- The wrappers do not work without private repository read access.
- The only network endpoints are `github.com` over SSH/HTTPS and
  loopback `127.0.0.1` for `commons serve`.
