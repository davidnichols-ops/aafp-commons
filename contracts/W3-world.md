# W3 World Schema and Loopback Replication Contract

Status: implementation contract; W3 remains uncommitted until the conductor authorizes a commit.

## Frozen world object

`GET /world` and the `commons_world` MCP tool return one JSON object with exactly these fields:

```text
packet_set_merkle
local_tip
peer_tips
fork_ids
conflict_ids
resolution_ids
packet_count
posture
agent_id
constitution
```

`agent_id` is `null` in source posture. `constitution` is `null` until the home is initialized or a constitution is assumed through the existing admission surface. Existing conflict identifiers are retained; W3 does not delete or rewrite them.

## Two-home replication law

The acceptance test uses two server processes and two distinct temporary `COMMONS_HOME` directories. One initialized subject proposes one evidence-backed packet through the existing W2 proposal path. The other initialized node pulls the signed packet over loopback HTTP from the first node and admits it through `CommonsRepository.submit`, preserving the existing signing, constitution, policy, object, and ledger formats.

The legacy mesh/node implementation contains replication concepts, but the W1 `commons serve` endpoint did not expose a usable packet replication route in this tree. W3 therefore adds only the minimum loopback HTTP pull: the source serves signed packets and the peer requests them through `/replicate`. This is HTTP pull, not QUIC or a new transport protocol.

After the pull, both `/world` objects must have equal `packet_set_merkle` values. `local_tip` may differ because each home records its own local ledger authority. The test must fail if any frozen schema field is missing.

## Scope boundary

W3 does not change MCP tool names, add network discovery, add DNS, add packaging or dependency fetching, invent vector search, delete conflict IDs, or create a second ledger format.
