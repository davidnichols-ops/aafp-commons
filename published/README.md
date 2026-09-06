# Published Public Snapshots

This directory contains published public snapshots from AAFP Commons nodes.
Each snapshot is a self-contained JSON file with signed KnowledgePackets
that can be imported into any local Commons node.

## Snapshot Format

Schema: `aafp.commons/research-snapshot@1`

Each snapshot contains:
- `packets` — array of signed KnowledgePacket objects (Ed25519-signed, content-addressed)
- `constitutions` — constitution manifests referenced by the packets
- `count` — number of packets
- `schema` — the snapshot schema identifier

## Verification

Every packet in a snapshot is cryptographically signed. To verify:

```bash
# Import into a local commons node (verifies all signatures)
commons sharing import <snapshot> <commons-home>

# Or verify without importing
commons sharing verify <snapshot>
```

## Available Snapshots

| File | Source | Packets | Date |
|------|--------|---------|------|
| `maos-lessons-public-2026-09-05.json` | MAOS (mac-ai-os) | 168 | 2026-09-05 |

## Provenance

Snapshots are exported from local Commons nodes. Only packets with
`visibility: "public"` are included. PII is stripped before export
via the MAOS curation pipeline (see `app/commons_curate.py` in mac-ai-os).

The signing identity's agent_id is included in each packet. The
corresponding public key can be verified against the node's
`identity.json` if the node is known.
