# R1 Ironclad Dependency Contract

## Purpose

Reproduce the real dependency situation for `aafp-commons` against the
`ironclad` package declared in `pyproject.toml`, in a clean temporary
environment that does not read or use `/Users/david/Projects/ironclad` to
make the install pass. Record the exact resolver error and inventory the
ironclad API symbols imported by `src/aafp_commons`.

## Constraints

- Clean temporary environment under `/tmp/commons-pass5-r1-*`.
- Do NOT read or use `/Users/david/Projects/ironclad` to make the install pass.
- No network workaround, PyPI publish, Vast, SSH, npm/brew, or `git add -A`.
- Do not modify source, pyproject, ledger data, tests, or docs other than
  this contract.

## Dependency declaration (pyproject.toml)

```toml
[project]
dependencies = [
    "ironclad>=1.0.0",
]

[tool.uv.sources]
ironclad = { path = "../ironclad", editable = true }
```

The dependency requires `ironclad>=1.0.0`. The `[tool.uv.sources]` table
overrides the resolver to pull ironclad from a local editable path at
`../ironclad` (relative to the project root). The lockfile records this as
`source = { editable = "../ironclad" }` at version `1.0.0`, with transitive
dependencies `cbor2` and `cryptography`.

## PyPI reality

PyPI publishes an unrelated package named `ironclad` at version `0.1.0`
(summary: "Runtime contracts and predicate-based validation for Python.").
It does NOT satisfy `>=1.0.0` and does NOT provide the `ironclad.trust` or
`ironclad.canon` modules consumed by this project. The local path source is
the only satisfying distribution; there is no public wheel or sdist for the
ironclad v1.0.0 that this project depends on.

## Ironclad API inventory (imported by src/aafp_commons)

Two modules, four distinct symbols:

| Symbol | Module | Imported by |
|---|---|---|
| `Identity` | `ironclad.trust` | w1.py, publication.py, cli.py, sharing.py, repository.py, signing.py, ledger.py |
| `Evidence` | `ironclad.trust` | signing.py |
| `Receipt` | `ironclad.trust` | signing.py |
| `content_digest` | `ironclad.canon` | publication.py, index.py, signing.py, ledger.py |

Import statements (verbatim):

```python
# w1.py:16
from ironclad.trust import Identity

# publication.py:11-12
from ironclad.canon import content_digest
from ironclad.trust import Identity

# index.py:9
from ironclad.canon import content_digest

# cli.py:9
from ironclad.trust import Identity

# sharing.py:8
from ironclad.trust import Identity

# repository.py:9
from ironclad.trust import Identity

# signing.py:10-11
from ironclad.canon import content_digest
from ironclad.trust import Evidence, Identity, Receipt

# ledger.py:17-18
from ironclad.canon import content_digest
from ironclad.trust import Identity
```

The string literal `"ironclad-ed25519-v1"` also appears as a scheme marker
in `signing.py` (lines 31, 53) and `ledger.py` (lines 70, 90); these are
data values, not API surface.

## Reproduction

Environment: `/tmp/commons-pass5-r1-<timestamp>` created by copying
`pyproject.toml` and `src/` from the project tree. The `../ironclad` path
source is intentionally absent. `uv sync` is run with no access to the
local ironclad checkout.

### Resolver error

Environment: `/tmp/commons-pass5-r1-1788647294` (copies of `pyproject.toml`
and `src/` only; `../ironclad` intentionally absent).

#### With path source (real pyproject.toml, as-is)

```
$ cd /tmp/commons-pass5-r1-1788647294 && uv sync --no-progress
Using CPython 3.14.7 interpreter at: /opt/homebrew/opt/python@3.14/bin/python3.14
Creating virtual environment at: .venv
error: Distribution not found at: file:///private/tmp/ironclad
```

Exit code: `2`

The `[tool.uv.sources]` entry `ironclad = { path = "../ironclad", editable = true }`
resolves to `/tmp/ironclad` (shown as `file:///private/tmp/ironclad` because
`/tmp` symlinks to `/private/tmp` on macOS). No distribution exists there, so
uv aborts before reaching PyPI.

#### Without path source (PyPI fallback, for confirmation)

With the `[tool.uv.sources]` block stripped, uv falls back to PyPI and finds
only the unrelated `ironclad==0.1.0`, which does not satisfy `>=1.0.0`:

```
$ uv sync --no-progress
  × No solution found when resolving dependencies:
  ╰─▶ Because only ironclad==0.1.0 is available and your project depends on
      ironclad>=1.0.0, we can conclude that your project's requirements are
      unsatisfiable.
      And because your project requires aafp-commons[dev], we can conclude
      that your project's requirements are unsatisfiable.
```

Exit code: `1`

This confirms there is no public distribution of the ironclad v1.0.0 that
this project depends on. The local path source is the only satisfying
distribution, and it is absent from the clean environment.

## Conclusion

The project has a hard, unresolvable dependency on a private local ironclad
v1.0.0 that is not published to PyPI. Any clean install without the
`../ironclad` path source fails at resolution time. The consumed API surface
is `ironclad.trust.{Identity,Evidence,Receipt}` and
`ironclad.canon.content_digest`.
