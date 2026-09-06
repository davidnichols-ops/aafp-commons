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
    },
    {
      "name": "env.json",
      "media_type": "application/json",
      "bytes": 512,
      "sha256": "sha256:…",
      "role": "environment",
      "disclosure": "public"
    },
    {
      "name": "step1.log",
      "media_type": "text/plain",
      "bytes": 22011,
      "sha256": "sha256:…",
      "role": "output",
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
method:

- configs, commands, lockfiles, environment records
- captured stdout/stderr or structured logs
- small golden outputs
- the exact script that was run

Do not include:

- secrets, tokens, cookies, private keys
- home-directory paths you are not willing to publish
- internal hostnames or ticket URLs
- model weights unless the claim is about those weights and disclosure
  allows it
- a second copy of the claim text pretending to be evidence

## Redaction

If a file or field cannot leave the home:

1. Produce a redacted copy.
2. Hash the redacted bytes separately.
3. Record `redaction` as a transformation from original digest to public
   digest, with the rule used (path-strip, URL-drop, secret-mask).
4. Never claim the redacted digest is the original.

## Method records

A verifier may only mark `reproduced` when:

- the method name is the one written on the claim or bundle
- the input digests match
- the command actually ran in this home
- the expected predicate was checked against captured output

If the method did not run, the result is `unavailable`, not a fake pass.

## Claim-to-evidence fit

The claim scope must be smaller than or equal to what the files can support.

| claim | required files |
| --- | --- |
| config parsed | config + parser output |
| one training step ran | config + command + env + step log |
| eval score S | eval script + dataset pin + results file |
| model quality | not supported by a one-step log |

A bundle that supports a one-step run does not support “the model is good.”

## Custodian checklist

- [ ] Every file listed in `manifest.json` is present and hashes.
- [ ] No private path or URL remains in public metadata.
- [ ] `disclosure` is set per file, not once for the bundle.
- [ ] Method is named and rerunnable or explicitly marked observational.
- [ ] Bundle digest is pinned on the packet before signing.
