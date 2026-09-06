from aafp_commons.verification import VerificationResult


def test_conflicting_results_remain_distinct():
    first = VerificationResult("claim", ("sha256:a",), "m", "supported", (), "verifier-a", "p")
    second = VerificationResult("claim", ("sha256:b",), "m", "failed", (), "verifier-b", "p")
    assert first.to_dict()["verification_id"] != second.to_dict()["verification_id"]
