# Q2 Package-Data Contract

Status: implementation contract; Q2 remains uncommitted until the conductor
authorizes a commit. This contract verifies that built-in constitution
manifests and protocol schemas are bundled into the built wheel and
reachable from an installed package without reading the source tree.

## Objective

Guarantee that `constitutions/grok-truth-seeking/1.0.0.json` (and the other
built-in constitution JSON files) ship inside the wheel and that their
content-addressed digests are available from the installed package alone.
The contract inspects the wheel manifest and the installed package; it does
not modify CI, README, INSTALL, or publishing.

## Scope

- Inspect `dist/aafp_commons-0.1.0-py3-none-any.whl` for bundled
  `aafp_commons/constitutions/<id>/<version>.json` entries.
- Confirm `constitutions/grok-truth-seeking/1.0.0.json` is present in the
  wheel and that its manifest digest matches the programmatic
  `GROK_TRUTH_SEEKING_MANIFEST.manifest_digest`.
- Confirm the digest is obtainable from an isolated install (no source
  checkout on `PYTHONPATH`, no reads of `/Users/david/Projects`).
- Add a focused regression test that asserts the bundled constitution JSON
  is reachable via `importlib.resources` and that its digest matches the
  programmatic package manifest.

## Out of scope

- Committing, pushing, publishing, or registering anything.
- Modifying `README.md`, `INSTALL`, `CHANGELOG.md`, or CI.
- PyPI, npm, brew, or any external registry.
- New MCP server names or dependency additions.
- Running or mutating `/tmp/commons-sim-*`. CLI checks use
  `COMMONS_HOME=/tmp/commons-pass4-*` only.
- `git add -A` or any bulk staging operation.

## Package configuration

`pyproject.toml` already declares the wheel package-data inclusion:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/aafp_commons"]

[tool.hatch.build.targets.wheel.force-include]
"protocols" = "aafp_commons/protocols"
"constitutions" = "aafp_commons/constitutions"
```

This places the repository-root `constitutions/` and `protocols/` trees
inside the `aafp_commons` package in the wheel. The built wheel
`dist/aafp_commons-0.1.0-py3-none-any.whl` contains:

- `aafp_commons/constitutions/anthropic-cc0/1.0.0.json`
- `aafp_commons/constitutions/gpt-astra-6/1.0.0.json`
- `aafp_commons/constitutions/grok-truth-seeking/1.0.0.json`
- `aafp_commons/protocols/*.schema.json`

No `pyproject.toml` change was required — the existing `force-include`
configuration is sufficient.

## Verification

1. Wheel contents include the constitution JSON:

   ```bash
   python3 -c "import zipfile; z=zipfile.ZipFile('dist/aafp_commons-0.1.0-py3-none-any.whl'); \
   assert 'aafp_commons/constitutions/grok-truth-seeking/1.0.0.json' in z.namelist()"
   ```

2. Isolated install (no source checkout) resolves the digest:

   ```bash
   rm -rf /tmp/commons-pass4-verify
   python3 -m venv /tmp/commons-pass4-verify
   /tmp/commons-pass4-verify/bin/pip install \
     /Users/david/Projects/ironclad/dist/ironclad-1.0.0-py3-none-any.whl \
     /Users/david/Projects/aafp-commons/dist/aafp_commons-0.1.0-py3-none-any.whl
   cd /tmp && /tmp/commons-pass4-verify/bin/python -c "
   from importlib.resources import files
   from aafp_commons.constitutions import ConstitutionManifest
   from aafp_commons.packages.grok_truth_seeking import GROK_TRUTH_SEEKING_MANIFEST
   bundle = files('aafp_commons').joinpath('constitutions','grok-truth-seeking','1.0.0.json')
   assert bundle.is_file()
   m = ConstitutionManifest.from_dict(__import__('json').loads(bundle.read_text()))
   assert m.manifest_digest == GROK_TRUTH_SEEKING_MANIFEST.manifest_digest
   print('DIGEST_MATCH: True', m.manifest_digest)
   "
   ```

3. CLI install-all + verify from an isolated home:

   ```bash
   rm -rf /tmp/commons-pass4-cli
   COMMONS_HOME=/tmp/commons-pass4-cli \
     /tmp/commons-pass4-verify/bin/aafp-commons constitutions install-all /tmp/commons-pass4-cli
   /tmp/commons-pass4-verify/bin/aafp-commons constitutions verify /tmp/commons-pass4-cli
   ```

## Acceptance

- `dist/aafp_commons-0.1.0-py3-none-any.whl` contains
  `aafp_commons/constitutions/grok-truth-seeking/1.0.0.json`.
- From an isolated install, `importlib.resources.files("aafp_commons")`
  resolves the bundled constitution JSON and its manifest digest equals
  `GROK_TRUTH_SEEKING_MANIFEST.manifest_digest`
  (`sha256:120f1a8b1f6d080d45d8a26a53df6a01862f72e8dcfa155ac76d65de3c8b317c`).
- `aafp-commons constitutions install-all` and `constitutions verify`
  succeed with `COMMONS_HOME=/tmp/commons-pass4-*`.
- A focused regression test (`tests/test_package_data.py`) asserts the
  bundled constitution JSON is reachable and digest-matches the
  programmatic manifest.
- No `pyproject.toml` change is required; the existing `force-include` is
  sufficient.
- No commits, no README/INSTALL/CI edits, no PyPI/npm/brew, no
  `/tmp/commons-sim-*` mutation.
