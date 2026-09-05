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
