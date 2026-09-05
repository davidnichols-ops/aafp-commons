# Two terminals, two homes

This example keeps each node's identity and ledger separate. Use two shells:

## Terminal A: the first subject

```bash
export COMMONS_HOME=/tmp/commons-a
commons init
commons serve --port 8081
```

Start `commons mcp` in another shell using the same `COMMONS_HOME`, then call
`commons_propose` with evidence such as:

```json
{
  "namespace": "commons/example",
  "claim": "The cache is safe for this workload.",
  "evidence": [{"kind": "test", "uri": "artifact://run/cache-safe"}]
}
```

## Terminal B: a second subject

```bash
export COMMONS_HOME=/tmp/commons-b
commons init
commons serve --port 8082
```

Call `commons_propose` with the contrary evidence-backed claim:

```json
{
  "namespace": "commons/example",
  "claim": "The cache is unsafe for this workload.",
  "evidence": [{"kind": "test", "uri": "artifact://run/cache-unsafe"}]
}
```

These claims are a contradiction for a later review. The current tree preserves
packet and ledger data but does not yet create conflict or resolution packets
from semantic contradictions. Resolution is not in this tree yet; inspect
`commons_world` and do not treat either claim as automatically authoritative.
