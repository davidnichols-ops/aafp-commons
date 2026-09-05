# P2 GitHub Origin Contract

Status: implementation contract; P2 does not commit, push code, or modify
repository content. It only inspects the remote configuration and, if
permitted and authenticated, establishes a private GitHub origin for the
existing local repository.

## Objective

Ensure the AAFP Commons repository has exactly one private GitHub origin
under the `davidnichols-ops` account, without replacing an existing origin,
without publishing as public, and without committing or modifying any
in-tree content.

## Scope

1. Inspect `git remote -v` to determine whether an `origin` remote already
   exists.
2. If `origin` already exists, do not replace it. Attempt to push `main` to
   `origin` only if authentication works. If auth fails, stop and report.
3. If no `origin` exists, create a private repository via
   `gh repo create davidnichols-ops/aafp-commons --private --source . --remote origin`.
   Never use `--public`. If the name is unavailable, fall back to the
   existing repository name as private and set `origin` only if the command
   explicitly succeeds.
4. If authentication fails at any step, stop without workarounds and report
   `auth blocked`.

## Out of scope

- Committing, staging, or modifying any tracked file.
- Modifying code, README, PASS logs, CI, or simulation homes.
- SSH or Vast operations.
- Publishing packages (PyPI, npm, etc.).
- Using `git add -A` or any bulk staging operation.
- Replacing an existing `origin` remote.
- Creating a public repository under any circumstances.
- Rewriting git history.

## Acceptance

- `contracts/P2-origin.md` exists and documents the origin handling.
- The final state of `git remote -v` is reported.
- Either the remote URL is returned, or the exact blocked reason is
  returned (e.g. `auth blocked`, `name unavailable`).
- No commits are made.
- No code, README, PASS logs, CI, or simulation homes are modified.
- No `git add -A` or bulk staging is performed.
- If `origin` already existed, it was not replaced.
