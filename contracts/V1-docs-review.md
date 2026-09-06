# V1 Contract — Handbook, custom constitutions, review plane

Status: docs and schemas pushed to main.

Parent: V0 verify. Does not weaken V0 state separation.

## Delivered

- `docs/HANDBOOK.md`
- `docs/EVIDENCE.md`
- `docs/CONSTITUTIONS.md`
- `docs/REVIEW.md`
- `docs/AGENTS-HANDBOOK.md`
- `constitutions/_template/1.0.0.json`
- `examples/constitutions/lab-notebook/1.0.0.json`
- `protocols/review-result@1.schema.json`
- `protocols/evidence-bundle@1.schema.json`

## Invariants

README stays ≤ 80 lines. Constitutions remain admission policy plus advisory guidance. Custom packages use `constitution-manifest@1`. Review results are signed packets. Reads do not dereference external evidence. Same-operator review is not independent by default.
