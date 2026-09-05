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
- Do not assume a constitution unless the user said `join` or `commons.json`
  has `join: true`.
- Proposals need evidence.
- Source posture is read-only.
