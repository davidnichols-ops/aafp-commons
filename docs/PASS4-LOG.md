# Commons Autonomous Pass 4 Log

Status: private-repository installation pass; no public visibility and no
PyPI publication.

## Results

- Q1/Q4 committed as `5603187`: `docs/INSTALL.md` contains the exact private
  SSH and HTTPS `uv tool install` commands, module MCP invocation, and an
  isolated `COMMONS_HOME` example. README remains 73 lines.
- Q2 committed as `90c0b06`: the existing Hatch `force-include` bundles
  `constitutions/`. The isolated wheel contains
  `grok-truth-seeking/1.0.0.json`; its digest matches the programmatic
  manifest. The focused package-data test passes.
- Q3 committed as `7e20026`: `COMMONS_HOME=/tmp/commons-pass4-q3 uv run
  --no-sync commons --help` exits 0 and exposes the frozen W1 commands.
- Q4 CI now has an `install-from-wheel` job that builds a wheel, installs it
  into a temporary environment, and runs `python -m aafp_commons world`.

## Packaging probe boundary

The wheel install path found the bundled constitutions, but dependency
resolution for `ironclad>=1.0.0` attempted the public index and failed after
three retries because DNS was unavailable. Installing the wheel with
`--no-deps` then failed at import because `ironclad` is required. No source
checkout was read to bypass this, and no package metadata or PyPI workaround
was invented.

## Verification

- Permitted regression subset: 197 passed, 3 skipped; Ruff clean.
- Focused package-data test: 3 passed.
- Endpoint grep: clean.
- W9/W11 three-home simulations were not rerun and frozen simulation homes
  were not touched.
- Q6 final log commit and private-origin push: pending.
