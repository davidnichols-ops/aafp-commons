import json

from aafp_commons.verification import check_bundle


def test_changed_evidence_fails_digest(tmp_path):
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps({"evidence_id": "e", "files": [{
        "path_rel": "run.txt", "sha256": "sha256:" + "0" * 64, "bytes": b"changed".hex()
    }], "missing": []}))
    assert check_bundle(bundle)["digest_checked"] is False
