# Review agent

Commons needs a reviewer the way Grokipedia used Grok: a second agent reads
a candidate and decides whether it may be displayed or relied on. Commons
does not copy Grokipedia’s failure modes.

Kept: users propose; an agent reviews; strangers do not freely rewrite the object.

Refused: a silent frozen queue; reviewer and publisher collapsing into one
identity; “Fact-checked by …” badges that hide missing sources; remote fetch
during read; treating model prose as evidence.

## Pipeline

```text
propose -> admit -> enqueue review -> mechanical spam screen
       -> constitution rubric -> signed review result -> consumer policy
```

Admission still lets a false well-formed claim in. Review makes that visible.

## Decision enum

`accept-display` `need-evidence` `reject-spam` `reject-scope`
`reject-constitution` `conflict` `escalate`

None of these set `supported` or `rely_ok` by themselves.

Same-operator reviews are not independent by default.
If no reviewer is running, the queue stays `in-review` with a timestamp.
