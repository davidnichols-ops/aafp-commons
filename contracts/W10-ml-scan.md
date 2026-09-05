# W10 Contract — Local ML Evidence Index

Status: implementation contract; W10 remains uncommitted until the conductor
authorizes a commit.

## Objective

Produce one in-tree evidence index that catalogs the usable machine-learning
trainer, config, and log artifacts that already exist under
`/Users/david/Projects/**`. The index is read-only with respect to every
project except `aafp-commons`: W10 does not modify, retrain, re-export, or
re-download anything in any other project tree.

## Deliverables

- `contracts/W10-ml-scan.md` — this contract.
- `examples/ml-evidence-index.md` — the index itself, listing every included
  artifact with its absolute path, file type, byte size, mtime, and a sha256
  digest computed from the file during this session.

## Scan rules

1. Scan only files that already exist on disk under
   `/Users/david/Projects/**`. Do not run training, download weights, fetch
   from HuggingFace, use Vast, use GPUs, or add dependencies.
2. Include only artifacts that are directly usable as ML evidence: trainer
   scripts, training configs, generation configs, tokenizer configs, training
   logs, evaluation result JSON, training-result CSV/PNG, run metadata, model
   cards, deployment manifests (Modelfile, CoreML mlpackage manifest), and
   provenance/determinism reports.
3. Exclude `.git`, `.venv`, `node_modules`, `__pycache__`, `.mypy_cache`,
   `.pytest_cache`, `.ruff_cache`, `dist`, and `.DS_Store` paths.
4. Exclude upstream-only forks of `peft`, `trl`, `transformers`, and
   `roboflow/inference` unless they contain local, non-upstream artifacts.
   This scan found no local artifacts in those forks.
5. Do not invent metrics. Any metric quoted in the index must be copied
   verbatim from a cited artifact file, with its source path stated.
6. Each entry records: absolute path, file type, byte size, mtime (YYYY-MM-DD),
   and sha256 digest. Digests are computed by `shasum -a 256` during this
   session.
7. Empty or negative findings are reported explicitly, not omitted.

## Write scope

W10 writes exactly two files, both inside `aafp-commons`:

- `contracts/W10-ml-scan.md`
- `examples/ml-evidence-index.md`

No other project tree is modified. No commits, no git staging, no
`.DS_Store` creation. No new dependencies. No registry, hosted service, or
network access.

## Acceptance

- `examples/ml-evidence-index.md` exists and lists real files with absolute
  paths under `/Users/david/Projects/`.
- Every listed digest matches `shasum -a 256 <path>` run independently.
- No listed path points at a file that does not exist on disk.
- The index records empty/negative findings for projects that were scanned
  but contained no usable ML artifacts.
- The existing test suite remains at least `192 passed`; W10 adds no tests.
- No file outside `aafp-commons/contracts/W10-ml-scan.md` and
  `aafp-commons/examples/ml-evidence-index.md` is written.

## Out of scope

- Training, fine-tuning, quantization, export, or weight download.
- Vast, SSH to remote GPUs, or any network operation.
- Modifying any project other than `aafp-commons`.
- W1 CLI, W2 MCP, W3 world schema, W5 packaging, W6 mDNS, W8 agent docs.
- New dependencies, MCP tool names, or constitution changes.
- Inventing, estimating, or projecting metrics not present in the cited
  files.
