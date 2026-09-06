import pytest

from aafp_commons.verification import VerificationError, export_safe


def test_private_reference_requires_redaction_record():
    with pytest.raises(VerificationError):
        export_safe({"disclosure": "private", "path": "/Users/david/secret.txt"})


def test_redacted_artifact_is_a_distinct_export():
    value = {"disclosure": "redacted", "source_transform": {"kind": "remove-path"},
             "sha256": "sha256:" + "a" * 64}
    assert export_safe(value) == value
