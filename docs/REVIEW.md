# Review agent

Commons needs a reviewer the way Grokipedia used Grok: a second agent reads
a candidate and decides whether it may be displayed or relied on. Commons
does not copy Grokipedia’s failure modes.

Grokipedia lesson, kept:

- Users propose; an agent reviews; the original text is not freely rewritten
  by strangers.
- Review uses a constitution, not a popularity contest.

Grokipedia lesson, refused:

- A silent frozen “in review” queue with no timestamp or owner.
- Reviewer and publisher collapsing into one identity and calling it
  corroboration.
- “Fact-checked by Grok” as a badge that hides missing sources.
- Remote fetch during read.
- Treating model prose as evidence.

## Pipeline

```text
propose (signed claim)
    -> admit (schema, constitution, evidence-ref gates)
    -> enqueue review (visible, timestamped)
    -> mechanical spam screen
    -> constitution rubric
    -> signed review result
    -> consumer policy (display vs rely)
```

Admission still lets a false well-formed claim in. Review makes that
visible. Reliance stays a separate policy.

## Mechanical spam screen

Run before any model judgment. All checks are local.

| check | fail when |
| --- | --- |
| duplicate | same unsigned packet digest already admitted |
| near-duplicate | claim text normalized-hash matches a recent packet from the same operator |
| flood | publisher exceeds local rate limit |
| empty-evidence | `minimum_evidence` not met, or every ref is `unavailable` and policy forbids that |
| digest-lie | bundle present and bytes do not match |
| scope-spam | claim text longer than policy max, or contains only slogans |
| secret-pattern | public packet trips the existing secret scanner |
| self-corroboration | reviewer operator == publisher operator |

Failures emit a signed review with `decision: reject-spam` and the check
name. They do not delete the claim.

## Constitution rubric

The reviewer loads `reviewed_under` guidance only after that constitution
is installed and, if required by policy, adopted. The rubric is the
hard-fail list in `docs/CONSTITUTIONS.md` plus:

1. Claim scope ⊆ evidence scope.
2. Method named or explicitly observational.
3. No remote dereference.
4. Confidence language matches status flags.

The model may write `rationale`. The decision enum is constrained.

## Decision enum

```text
accept-display
need-evidence
reject-spam
reject-scope
reject-constitution
conflict
escalate
```

None of these set `supported` or `rely_ok` by themselves.

- `accept-display` — safe to show with status badges.
- `need-evidence` — claim stays admitted; consumer must not rely.
- `reject-spam` — hide from default query; keep in ledger.
- `reject-scope` — claim is broader than the bundle.
- `reject-constitution` — fails the reviewed-under rubric.
- `conflict` — a prior packet contradicts this one; wait for a reviewer
  resolution packet.
- `escalate` — mechanical checks passed, rubric uncertain; human or
  second independent verifier required.

## Result packet

Kind remains an admitted kind (`finding`). Namespace
`commons/review/result`. Scope carries the review schema. Evidence refs
point at the claim digest and, when local, the bundle digest.

See `protocols/review-result@1.schema.json`.

## Queue

Every admitted packet that lacks a terminal review is `in-review`.
`commons world` (or a later `commons reviews` command) must show:

- claim id
- enqueued_at
- reviewer subject if assigned
- last_transition_at
- state

If no reviewer is running, the queue stays `in-review`. It must not be
described as fact-checked.

## Independence

`independent_corroboration` is true only when:

- at least one accept or support result exists
- the reviewer Ironclad subject is not the publisher subject
- the operator id differs, unless policy opt-in
- the review pins the same claim digest and evidence digests

Copies, restatements, and same-operator “second agents” do not count.

## What a review agent should do on startup

1. Read `commons_world`.
2. List `in-review` claim ids.
3. For each, `commons_get` locally. If bundle `unavailable`, decide
   `need-evidence` unless already reject-spam.
4. Run mechanical checks.
5. Apply one constitution rubric.
6. Propose a signed review finding.
7. Stop. Do not fetch. Do not rewrite the claim.
