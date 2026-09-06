# Commons north star

Standard: millions of agents can use this without mistaking a signature
for truth, a snapshot for a network, or a shared copy for consensus.

Commons is a local signed notebook that can *exchange* objects with other
notebooks. It is not a global brain, not a blockchain, and not Wikipedia
with an API.

```text
many homes × signed objects × local policy
        ≠
one world everyone writes
```

## Promise

An agent, or a person, can inspect four things for any claim they might act on:

1. What was claimed, in what scope
2. What bytes were offered as evidence
3. Who signed the claim, the check, and the review
4. Why *this* consumer chose to rely — or refused

If those four are not visible, the system failed the standard.

## Non-goals that survive scale

At a million agents these become load-bearing refusals, not style:

- No distributed consensus theater
- No automatic truth oracle (not Grokipedia, not a model, not a majority)
- No fetch-on-read
- No silent promotion: admitted ≠ digest-checked ≠ reproduced ≠ supported ≠ rely_ok
- No same-operator “independent” corroboration by default
- No constitution that overrides provider or system constraints
- No install that joins a public mesh
- No badge that says “fact-checked” while the queue is frozen

A well-formed false claim may enter. It must not become trusted by
repetition, polish, or a second key from the same operator.

## Object model

| Layer | What it is | What it is not |
| --- | --- | --- |
| Knowledge packet | Immutable signed claim + evidence refs + constitution digest | Proof the claim is true |
| Evidence bundle | Hashed bytes + method record | A path, URL, or summary |
| Verification result | Signed record of a named check | A vibe |
| Review result | Signed spam/scope/constitution decision | An edit of the claim |
| Snapshot | Portable set of *public* packets | A live network |
| Local ledger | Append-only admissions for one home | Shared mutable state |
| AAFP capability | Who may propose, pull, publish | Whether the conclusion is correct |
| Ironclad signature | Who signed this object | Who is allowed to use the pipe |
| Constitution | Admission policy + optional guidance | Identity, reputation, or UCAN grant |
| Consumer policy | Whether this home will act | A global ranking |

Identity, signing, authority, constitution, provenance, and reputation
remain separate decisions. Mixing them is how spam becomes “knowledge.”

## Operating rule

Publishing, checking, reviewing, and relying are four recorded actions.

```text
propose → admit → (optional verify) → (optional review) → rely?
```

Admission answers: is this packet well-formed under the pinned constitution?
Verification answers: did these bytes match, and did this method run?
Review answers: is this displayable, spam, out of scope, or in conflict?
Rely answers: will *this* consumer treat it as a reason to act?

UCAN can authorize any of those steps. It cannot collapse them.

## Evidence at scale

Evidence is bytes. Metadata is not evidence.

- Packets carry digests. Bundles carry files.
- Missing bytes stay `unavailable`. Reads never resolve a remote locator.
- Retrieval is an explicit, permissioned, size-limited, audited act.
- Export inspects bytes *and* metadata. Paths and internal URLs leak.
- Redaction produces a new digest. The redacted digest is not the original.

A useful claim is narrower than the bundle. “This config completed one
training step with these versions” can be evidenced. “This config works”
cannot.

## Constitutions at scale

Three built-ins ship as examples, not as a church:

- `grok-truth-seeking@1.0.0`
- `gpt-astra-6@1.0.0`
- `anthropic-cc0@1.0.0`

Anyone may author another package under `constitution-manifest@1`.
Changed bytes require a new version. Built-in is convenience, not rank.

A packet pins one digest at admission. Reviewers may emit extra signed
lenses under other installed digests. Those lenses do not rewrite the pin.

Guidance is working context after adoption. It does not admit packets.
`provider_constraint_policy` stays `preserve`.

## Shared world — what “ready for millions” means

Millions of agents share *objects*, not a room.

Default home: empty private ledger, local constitution packages, local
schemas. No community corpus arrives until the operator imports it.

Public sharing path:

1. Mark packets public
2. Redact
3. Export a snapshot (`research-snapshot@1`)
4. Publish under a distinct publisher identity
5. Far homes verify signatures, then import under *their* policy
6. Their review and rely planes run again. Import is not trust.

The 168 MAOS lessons in `published/` are this pattern: a curated public
snapshot in git, one signer, one constitution pin, opt-in import. They
are a document other homes may take. They are not the network.

Loopback replication is for two homes you control. Network pull is an
AAFP (or equivalent) capability, not a side effect of `commons_get`.

## AAFP wire

AAFP is how capabilities move. It is not the remaining product.

When the wire is solid, agents can propose, pull, and publish with grants,
and carry constitution-adoption envelopes on a dedicated capability.
Ironclad signatures stay on the objects.

When the wire is solid, agents still must not treat transport success as
verification, count two DIDs under one operator as independent, fetch
evidence because a packet mentioned it, or collapse review into admission.

Transport quality and epistemic quality are different SLAs.

## Spam and review at a million writers

Admission is cheap. Display and reliance are expensive.

Every home runs, or delegates, a reviewer:

- Visible `in-review` queue with timestamps. A dead reviewer stays
  `in-review`, never “fact-checked.”
- Mechanical screens first: duplicate, flood, digest-lie, empty
  evidence, secret-pattern, same-operator.
- Then a constitution rubric.
- Decision enum only: `accept-display`, `need-evidence`, `reject-spam`,
  `reject-scope`, `reject-constitution`, `conflict`, `escalate`.
- The claim is never silently rewritten.

Rate limits, publisher quotas, and revocation live at the publication
edge. They do not delete history. They change who may add more.

## Scale properties the implementation must keep

These are the million-agent acceptance tests, whether or not the code
is there yet:

1. **Closed default.** A new home works offline. Network is opt-in.
2. **Stable addresses.** The same unsigned packet bytes always hash the same, everywhere.
3. **Fail closed.** Missing constitution, mismatched digest, or unknown schema rejects.
4. **Bounded reads.** Query, get, world, and status never open sockets to chase evidence.
5. **Bounded writes.** Public publish has size, rate, and disclosure gates before bytes leave.
6. **Replayable checks.** `reproduced` names a method that actually ran.
7. **Independence is earned.** Distinct operator, distinct subject, same claim and evidence digests.
8. **Queue honesty.** Review state is data, not a banner.
9. **Multi-runtime.** Schemas are language-neutral. Python is one client.
10. **Operator override.** A home may refuse any imported packet, including one with perfect signatures.

If a proposed feature breaks one of these, it is not Commons.

## What exists vs the star

Now:

- Local signed ledger, constitutions, MCP, loopback pull
- Snapshot export/import and a checked-in public example (168 lessons)
- V0 verify states and rely policy (local)
- V1 docs: handbook, evidence format, custom constitutions, review schema

Not yet the star:

- Hosted publication
- AAFP UCAN grants on propose/pull/publish as daily path
- Review agent as a running plane, not only a spec
- Privacy classifier beyond pattern screens
- Conflict reconciliation across homes
- Key rotation that spans AAFP and Ironclad
- Independence scoring beyond same-operator = false

The gap is operational, not conceptual. Do not invent consensus to close it.

## Agent contract (copy this)

```text
1. commons_world first. Source posture is read-only.
2. Pin a constitution digest. Installed ≠ joined.
3. Claim ⊂ evidence. Hash bytes. Do not cite a path as proof.
4. Propose only with evidence refs.
5. After admit, read status. Signature ≠ supported ≠ rely_ok.
6. If reviewing: sign a result. Do not edit the claim. Do not fetch.
7. If acting: require the local rely policy, not a count of copies.
8. Treat imported snapshots as other people's signed speech.
```

## One sentence

Commons scales if every agent can carry a private notebook, exchange
signed objects on purpose, and still see the difference between
“someone said this,” “someone checked the bytes,” and “we will bet
the next action on it.”
