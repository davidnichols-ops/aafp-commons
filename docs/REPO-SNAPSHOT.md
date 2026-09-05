# AAFP Commons Repository Snapshot

Captured: 2026-09-05
Repository: `/Users/david/Projects/aafp-commons`

## Recent history

```text
c93ff50 feat(world): freeze /world schema and loopback HTTP pull
96ea872 feat(mcp): stdio server with frozen commons tools
a8422ee feat(cli): add commons home, init, serve, world, get
abeda33 Initial import of aafp-commons library tree.
```

The repository has four commits; `git log --oneline -15` returns these four
entries.

## Git status

Status captured after this snapshot file was created:

```text
 M AGENTS.md
 M README.md
?? .DS_Store
?? commons.json.example
?? constitutions/.DS_Store
?? contracts/W8-agent-docs.md
?? docs/REPO-SNAPSHOT.md
?? examples/two-terminals.md
?? src/.DS_Store
?? src/aafp_commons/.DS_Store
?? src/aafp_commons/__main__.py
?? tests/test_w8_docs.py
```

W8 remains uncommitted. The `.DS_Store` files are untracked and were not
staged.

## Requested audit and contracts

| File | Lines | Description |
| --- | ---: | --- |
| [docs/STATUS-0.3-GAP.md](STATUS-0.3-GAP.md) | 114 | 0.3 tree map, coverage, CLI, mesh presence, test baseline, and verdict |
| [contracts/W1-cli-home.md](../contracts/W1-cli-home.md) | 54 | Frozen `commons` CLI, home, `/world`, and W1 acceptance contract |
| [contracts/W2-mcp.md](../contracts/W2-mcp.md) | 70 | Frozen zero-configuration stdio MCP tools and W2 boundaries |
| [contracts/W3-world.md](../contracts/W3-world.md) | 34 | Frozen world schema and loopback HTTP pull contract |
| [contracts/W8-agent-docs.md](../contracts/W8-agent-docs.md) | 41 | Agent-facing documentation contract and W8 acceptance criteria |

## Agent instructions and project overview

| File | Lines | Description |
| --- | ---: | --- |
| [AGENTS.md](../AGENTS.md) | 26 | Project invariants plus MCP startup, posture, constitution, and evidence guidance |
| [README.md](../README.md) | 51 | Local Commons overview, quick start, MCP surface, and development commands |

The README is within the W8 limit of 80 lines.
