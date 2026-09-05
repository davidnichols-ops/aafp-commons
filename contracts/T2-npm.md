# T2 Contract — Private npm Shim for `@aafp/commons`

Status: implementation contract; T2 remains uncommitted until the conductor
authorizes a commit. This contract adds a private npm package manifest and a
single bin shim that delegates to the installed Python wheel. It does not
publish, pack against a registry, or perform any public action.

## Objective

Provide an optional npm-side entry point for environments that discover tools
through `npx` or a local `node_modules/.bin` path. The npm package is private,
declares no runtime dependencies, and contains no ledger, signing, policy, or
constitution logic. Its sole executable forwards every argument and the child
stdio streams to the installed Python package via
`python -m aafp_commons` (or `python3 -m aafp_commons`).

## Frozen interface

- Package name: `@aafp/commons`.
- `package.json` sets `"private": true` and `"version"` mirroring the Python
  package (`0.1.0`).
- `package.json` declares exactly one bin entry: `"commons"` →
  `"bin/commons.js"`.
- `package.json` declares no `dependencies` and no `peerDependencies`. The
  `engines` field requires `node >= 20` only because the shim uses
  `process.exitCode` assignment and `child_process.spawn` with `stdio: "inherit"`
  semantics available since Node 12; the floor is conservative, not a hard
  runtime constraint.
- `bin/commons.js` is an executable Node script (`#!/usr/bin/env node`) that:
  1. Resolves a Python interpreter by trying `python3` then `python` on
     `PATH`.
  2. Spawns `<python> -m aafp_commons <args...>` with `stdio: "inherit"`.
  3. Forwards the exit code from the child process.
  4. Contains no ledger, signing, policy, constitution, packet, or world
     logic. It does not parse Commons subcommands, read `COMMONS_HOME`, or
     interpret child output.
- The shim does not depend on the source tree. It relies solely on the
  installed Python wheel being importable as `aafp_commons` by the resolved
  interpreter.

## Scope

- Add `package.json` at the repository root.
- Add `bin/commons.js` at the repository root.
- Add this contract at `contracts/T2-npm.md`.

## Out of scope

- Modifying Python source under `src/`, `protocols/`, or `constitutions/`.
- Modifying `pyproject.toml`, `README.md`, `docs/INSTALL.md`, `CHANGELOG.md`,
  `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`, or `Makefile`.
- Modifying any test under `tests/` or any simulation home under
  `v03-evidence/` or `docs/sim-world-*.json`.
- Running `npm publish`, `npm pack` against a registry, `npm install` against
  a registry, or any public/network npm action.
- Adding `node_modules/`, `package-lock.json`, or `npm-shrinkwrap.json`.
- Reimplementing any ledger, signing, policy, constitution, packet, world, or
  MCP logic in JavaScript.
- Committing, pushing, `git add -A`, or any bulk staging operation.
- Introducing runtime npm dependencies of any kind.

## Verification

```bash
# Syntax check the shim without executing the Python delegation
node --check bin/commons.js

# Confirm the manifest is private and dependency-free
node -e "const p=require('./package.json'); \
  console.log('private='+p.private, 'deps='+JSON.stringify(p.dependencies||{}), \
  'bin='+JSON.stringify(p.bin))"
```

A functional smoke test (optional, not required by this contract) is:

```bash
COMMONS_HOME=/tmp/commons-t2-smoke node bin/commons.js --help
```

This must produce the same output as
`COMMONS_HOME=/tmp/commons-t2-smoke python3 -m aafp_commons --help` and exit
with the same code, because the shim forwards verbatim.

## Acceptance

1. `package.json` exists at the repository root with `"private": true`, no
   `dependencies`, no `peerDependencies`, and a single `bin.commons` entry
   pointing at `bin/commons.js`.
2. `bin/commons.js` exists, is executable, passes `node --check`, and forwards
   all arguments to `<python> -m aafp_commons` without reimplementing any
   Commons logic.
3. No file under `src/`, `protocols/`, `constitutions/`, `tests/`, `docs/`,
   `README.md`, `pyproject.toml`, `Makefile`, `LICENSE`, `CHANGELOG.md`,
   `CONTRIBUTING.md`, or `SECURITY.md` is modified.
4. No `node_modules/`, `package-lock.json`, or `npm-shrinkwrap.json` is
   created.
5. No `npm publish`, `npm pack`, registry `npm install`, or any public npm
   action is run.
6. No commit, no `git add -A`, no push.
