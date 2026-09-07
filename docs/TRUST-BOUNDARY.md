# Trust boundary

Two independent trust systems sit on the agent's MCP path. They answer
different questions and must not be collapsed into one.

## Path

```text
agent
  |
  |  (optional, local stdio) Trustcard proxy
  v
MAOS MCP  --  Commons MCP  --  local signed ledger
```

The agent speaks MCP. Trustcard wraps MCP calls. MAOS hosts the session.
Commons admits signed packets to the local ledger. The ledger is the terminal
sink; nothing downstream re-derives trust.

## What each answers

- **Trustcard** answers *may this call run, and is this still the server I
  approved?* It gates invocation: manifest fingerprint, danger fusion, per-call
  argument policy, auth scopes, signed receipts. It does not assess claim
  truth, evidence, or ledger admission.
- **Commons** answers *is this claim admitted, verified, and relied on?* It
  gates knowledge: signature, content address, evidence, conflicts, rely
  policy, constitution pin. It does not inspect the MCP transport, tool
  schemas, or caller identity at the wire.

Trustcard is about the wire. Commons is about the world. A call can pass
Trustcard and still produce a packet with `rely_ok: false`; a packet can be
relied on while the call that produced it would be blocked by Trustcard on a
different host.

## Local stdio: Trustcard is optional

On-box, stdio MCP between a trusted agent and `commons mcp` does not require
the Trustcard proxy. The process boundary is the trust boundary; the operator
owns both ends. Run `commons mcp` directly:

```bash
uv run --no-sync python -m aafp_commons mcp
```

Adding the local Trustcard proxy here is defense-in-depth, not a requirement.
It never changes ledger admission or rely outcomes.

## Off-box: pin manifest, then Trustcard

When Commons MCP is exposed beyond the operator's process tree (HTTP/SSE,
remote agent, shared host, third-party runtime), the wire is no longer
self-trusting. In that case:

1. Generate and pin a Trustcard manifest for the Commons server command so
   callers can verify capability continuity (Gate 1).
2. Front the exposed endpoint with the Trustcard proxy so every invocation is
   re-validated against the pinned descriptor and auth scopes (Gate 2).
3. Keep the ledger private by default; only explicitly public packets leave
   the client, per the north-star invariants.

Pinning the manifest is the TOFU step. The proxy is the runtime gate. Both
apply to the MCP edge only — they do not sign packets, change content
addresses, or alter `commons status` / `commons rely` results.

## Non-goals

- Trustcard does not sign knowledge packets or participate in admission.
- Commons does not fingerprint MCP servers or enforce call policy.
- Neither system makes a claim true. Truth is a verify result plus rely
  policy, recorded in the ledger, never asserted at the edge.
