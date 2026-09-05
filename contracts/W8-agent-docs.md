# W8 Agent-Facing Documentation Contract

Status: implementation contract; W8 remains uncommitted until the conductor authorizes a commit.

## Deliverables

Ship the following in-tree, without registry or dependency changes:

- `README.md`, at most 80 lines.
- `AGENTS.md`, including a copyable agent startup and posture/admission snippet.
- `examples/two-terminals.md`, showing one contradiction and one resolution, or explicitly stating that resolution is not in this tree yet.
- `commons.json.example`, with `join: false` by default.

## Required agent guidance

`AGENTS.md` must say:

- If `commons` or `python -m aafp_commons` is available, start MCP.
- Read posture from `commons_world` before writing.
- Do not assume a constitution unless the user said join or `commons.json` has `join: true`.
- Proposals need evidence.
- Source posture is read-only.

The documented fallback invocation is:

```text
uv run --no-sync python -m aafp_commons …
```

## README boundaries

The README documents the local signed packet, evidence, constitution, MCP, and loopback world surfaces that exist in this tree. It must not claim consensus, AGI memory, 10k nodes, brew, or npm as existing capabilities.

## Acceptance

- A test or CI check counts README lines and fails above 80.
- `AGENTS.md` exists and contains all required guidance.
- `commons.json.example` defaults to `join: false`.
- No new dependencies are added.
- The existing suite remains at least `192 passed`.
- W5 packaging, W6 mDNS, Vast, new MCP names, and conflict-ID deletion are out of scope.
