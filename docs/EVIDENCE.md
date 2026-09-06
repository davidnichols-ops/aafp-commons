# Evidence format

Evidence is bytes plus a description of those bytes. A path, URL, or summary
is not evidence.

## Bundle

A portable evidence bundle is a directory or archive with a manifest:

```text
bundle/
  manifest.json
  files/
    <safe-name>
  notes.md          # optional, human prose, not a substitute for files
```

`manifest.json`:

```json
{
  "schema": "aafp.commons/evidence-bundle@1",
  "bundle_id": "sha256:<digest of canonical manifest without bundle_id>",
  "created_at": "2026-09-06T14:00:00Z",
  "claim_scope": "config X loaded and completed one training step",
  "files": [
    {
      "name": "config.yaml",
      "media_type": "text/yaml",
      "bytes": 1842,
      "sha256": "sha256:…",
      "role": "input",
      "disclosure": "public"
    }
  ],
  "method": {
    "name": "one-training-step",
    "command": "python train.py --config config.yaml --max-steps 1",
    "expected": "process exit 0 and log contains 'step 1 done'"
  },
  "redaction": null,
  "origin_home": "local"
}
```

Hash the file bytes, not a pretty-printed view of them.

## EvidenceRef on a packet

```json
{
  "kind": "log",
  "digest": "sha256:…",
  "bundle_digest": "sha256:…",
  "status": "supplied",
  "local": true,
  "locator": "bundle:files/step1.log"
}
```

`status` values:

| status | meaning |
| --- | --- |
| `supplied` | A reference exists in the packet |
| `unavailable` | Bytes are not in this home |
| `digest-checked` | Local bytes match `digest` |
| `redacted` | Public artifact replaces a private original |

Reading a packet never changes `unavailable` into a fetch.

## What belongs in a bundle

Include only what a second process needs to inspect or rerun the stated
method.

Do not include secrets, private paths you will not publish, internal hostnames,
or a second copy of the claim text pretending to be evidence.

## Redaction

If a file or field cannot leave the home:

1. Produce a redacted copy.
2. Hash the redacted bytes separately.
3. Record `redaction` as a transformation from original digest to public digest.
4. Never claim the redacted digest is the original.

## Method records

A verifier may only mark `reproduced` when the named method actually ran in
this home against matching input digests. Otherwise the result is `unavailable`.

## Claim-to-evidence fit

The claim scope must be smaller than or equal to what the files can support.
A bundle that supports a one-step run does not support “the model is good.”

## Custodian checklist

- [ ] Every file listed in `manifest.json` is present and hashes.
- [ ] No private path or URL remains in public metadata.
- [ ] `disclosure` is set per file, not once for the bundle.
- [ ] Method is named and rerunnable or explicitly marked observational.
- [ ] Bundle digest is pinned on the packet before signing.
