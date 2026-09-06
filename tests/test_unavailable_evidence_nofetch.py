import pytest

from aafp_commons.verification import EvidenceBundle


def test_missing_bundle_is_unavailable_without_fetch(tmp_path):
    bundle = EvidenceBundle(("claim",), (), "private", missing=("https://example.invalid/x",))
    value = bundle.to_dict()
    assert value["missing"]
    with pytest.raises(FileNotFoundError):
        (tmp_path / "absent.json").read_text()
