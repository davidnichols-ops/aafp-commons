"""G-SIGN: signed VerificationResult verifies directly from payload, tamper fails."""

import copy
import json

from aafp_commons.identity import derive_agent_id
from aafp_commons.verification import (
    EvidenceBundle,
    record_verification,
    sign_object,
    verify_object,
)


def test_signed_verification_result_verifies(tmp_path, identity):
    verifier_id = derive_agent_id(identity.public_bytes())
    result = record_verification(
        tmp_path, "sha256:abc", "method-1", verifier_id, "unavailable", identity
    )
    assert result["signer_key_id"] is not None
    assert result["signature_b64"] is not None
    assert result["signer_public_key_b64"] is not None
    assert verify_object(result) is True


def test_unsigned_verification_result_does_not_verify(tmp_path):
    result = record_verification(
        tmp_path, "sha256:abc", "method-1", "aafp:verifier", "unavailable"
    )
    assert result.get("signer_key_id") is None
    assert result.get("signature_b64") is None
    assert verify_object(result) is False


def test_tampered_outcome_fails_verification(tmp_path, identity):
    verifier_id = derive_agent_id(identity.public_bytes())
    result = record_verification(
        tmp_path, "sha256:abc", "method-1", verifier_id, "unavailable", identity
    )
    tampered = copy.deepcopy(result)
    tampered["outcome"] = "supported"
    assert verify_object(tampered) is False


def test_tampered_signature_fails_verification(tmp_path, identity):
    verifier_id = derive_agent_id(identity.public_bytes())
    result = record_verification(
        tmp_path, "sha256:abc", "method-1", verifier_id, "unavailable", identity
    )
    tampered = copy.deepcopy(result)
    # Flip one character in the signature
    sig = tampered["signature_b64"]
    tampered["signature_b64"] = ("A" if sig[0] != "A" else "B") + sig[1:]
    assert verify_object(tampered) is False


def test_signed_evidence_bundle_verifies(identity):
    bundle = EvidenceBundle(
        claim_ids=("sha256:abc",),
        files=(),
        disclosure="private",
        missing=(),
    ).to_dict()
    signed = sign_object(bundle, identity)
    assert signed["signer_public_key_b64"] is not None
    assert verify_object(signed) is True


def test_tampered_evidence_bundle_fails(identity):
    bundle = EvidenceBundle(
        claim_ids=("sha256:abc",),
        files=(),
        disclosure="private",
        missing=(),
    ).to_dict()
    signed = sign_object(bundle, identity)
    tampered = json.loads(json.dumps(signed))
    tampered["disclosure"] = "public"
    assert verify_object(tampered) is False
