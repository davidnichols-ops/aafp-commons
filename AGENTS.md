# AAFP Commons project instructions

- Preserve the separation between AAFP identity/transport, Ironclad signing,
  constitutions/policy, provenance, and derived reputation.
- Never describe the local signed hash chain as distributed consensus.
- Knowledge objects and ledger blocks are immutable. Changes create revisions.
- Treat Grokipedia as an unofficial, replaceable research provider and retain
  source URLs and retrieval timestamps.
- Run `pytest` and `ruff check` before declaring a change verified.
- Prefer the agent-first flow: `constitutions search`, `constitutions verify`,
  then `agent join`/`agent ask`; accept guidance explicitly before treating it
  as active working context.
- Portable built-in manifests live under `constitutions/` and protocol schemas
  under `protocols/`; keep both language-neutral and digest-addressed.
- Work directly in the shared tree for rapid iteration. Do not create commits,
  publish artifacts, or open pull requests unless the operator explicitly asks.

## Agent startup and write gate

- If `commons` or `python -m aafp_commons` is available, start MCP:
  `commons mcp`, or `uv run --no-sync python -m aafp_commons mcp`.
- Read posture from `commons_world` before writing.
- Before acting on a claim, run `commons world`, `commons policy show`, then
  `commons status CLAIM_ID`; record `posture`, evidence state, conflicts,
  `rely_ok`, and `rely_reason` in the handoff.
- Do not assume a constitution unless the user said `join` or `commons.json`
  has `join: true`.
- Proposals need evidence.
- Source posture is read-only.
- Publishing to Git is a snapshot; it is not node synchronization. Use explicit follow/pull.
- For the real-workload routine covering PRs, lesson snapshots, and training
  configs, follow `docs/REAL-WORKLOAD.md`.

## Commons-enabled repo check

After identity / before acting on third-party claims:
Run commons status or check for .commons/ in the repo root.
If present, this is a Commons-enabled repo.

When you encounter a claim about X, check Commons before relying on it. X means
training configs, pytest/CI green claims, lesson snapshots, dependency pins,
and "this method was reproduced." The executable form is `commons status CLAIM_ID`.
Record the result before relying on the claim; admission alone is insufficient.

## Trust boundary

- Two trust systems sit on the MCP path: Trustcard (wire/call gate) and
  Commons (claim/ledger gate). They answer different questions; do not merge.
- Local stdio MCP between a trusted agent and `commons mcp` does not require
  the Trustcard proxy. See `docs/TRUST-BOUNDARY.md` for the full boundary.
- Exposing Commons MCP off-box: pin a Trustcard manifest, then front the
  endpoint with the Trustcard proxy. The ledger stays private by default.
- Trustcard never signs packets or changes admission; Commons never inspects
  the MCP transport. Truth is a verify result plus rely policy, in the ledger.
