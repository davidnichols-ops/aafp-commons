"""R2 compatibility tests for the vendored ironclad signing surface.

These tests pin the ``ironclad-ed25519-v1`` wire format to known vectors
derived from the original ironclad runtime, ensuring the vendored
``ironclad.canon`` and ``ironclad.trust`` modules produce byte-identical
output. They also exercise the full sign → verify → tamper → fail-closed
round-trip through ``aafp_commons.signing`` and ``aafp_commons.ledger``.
"""

from __future__ import annotations

import time
from pathlib import Path

from ironclad.canon import content_digest
from ironclad.trust import Evidence, Identity, Receipt

from aafp_commons.canonical import b64encode
from aafp_commons.identity import derive_agent_id
from aafp_commons.ledger import Ledger
from aafp_commons.models import (
    ConstitutionRef,
    EvidenceRef,
    KnowledgePacket,
    MethodRef,
)
from aafp_commons.signing import SignedPacket, sign_packet

# --- Wire-format vectors (from original ironclad 1.0.0 runtime) ---

_SEED = b"0123456789abcdef0123456789abcdef"
_SEED_KEY_ID = "sha256:u9AzT2bO23hKe7rnLxGohDfqrmW3b0DffmLWhVsHurU"
_SEED_PUB_HEX = "23bc54912c1e6e92c4a86825c867e27ffdc555bffbd4244f17a26abfffee965d"

_CD_A1 = "sha256:65ibSmIP0lmuAhgb2rT8Prbca0XrcyKZm7FBa84xiSY"
_CD_NESTED = "sha256:IfZM6aIatAlSzMpUlFIsaYm84byruABXFvgLEBZ3SCk"
_CD_LIST = "sha256:bFCaEUJkNphZSfanvoGR3Nn8k6fhJhS3aEQ_FKoh0Ww"
_CD_FLOAT = "sha256:JFBmrzIx4CsupT0vdySxhhEdAeZFh69xhJLAiRpIeW4"
_CD_NEG_ZERO = "sha256:Dpf7wF10WUZDygQzxegzzgcMdthcoLo7l5Iuy33oL7Y"
_CD_TRAILING_ZEROS = "sha256:wnKYP6lK2yxDdhrrPm1yCDiXPqkb1HSdpye0E9ooVMk"

_EV_NONCE = "fixednonce12345678901234"
_EV_DIGEST = "sha256:O3Ut1rb--TbTaonuaKdNavwY-MuEpauPiAAjo0RVWBI"
_EV_SP_HEX = (
    "a36664696765737478327368613235363a4f3355743172622d2d546254616f6e75614b64"
    "4e617677592d4d7545706175506941416a6f305256574249677375626a65637467706b74"
    "2d31323369707265646963617465781a616166702e636f6d6d6f6e733a7061636b65743a"
    "7369676e6564"
)
_RC_DIGEST = "sha256:IG0oIUNuE47YgolmdQQ60FnD1P2km3zYVLsjdBFilkE"
_RC_DIGEST_NONE = "sha256:NMDimnVRVd9x0aOi34IRce15A-gWjTlOQRJdYunjKLA"


# --- content_digest wire-format pinning ---


def test_content_digest_simple_dict() -> None:
    assert content_digest({"a": 1}) == _CD_A1


def test_content_digest_nested_sorted_keys() -> None:
    assert content_digest({"b": {"d": 1, "c": 2}, "a": 3}) == _CD_NESTED


def test_content_digest_list() -> None:
    assert content_digest([3, 1, 2]) == _CD_LIST


def test_content_digest_float() -> None:
    assert content_digest({"x": 1.5}) == _CD_FLOAT


def test_content_digest_negative_zero_equals_positive_zero() -> None:
    assert content_digest({"x": -0.0}) == _CD_NEG_ZERO
    assert content_digest({"x": 0.0}) == _CD_NEG_ZERO


def test_content_digest_trailing_zero_floats_canonicalized() -> None:
    assert content_digest({"x": 1.10}) == _CD_TRAILING_ZEROS


# --- Identity determinism ---


def test_identity_from_seed_key_id() -> None:
    ident = Identity.from_seed(_SEED)
    assert ident.key_id == _SEED_KEY_ID


def test_identity_from_seed_public_bytes() -> None:
    ident = Identity.from_seed(_SEED)
    assert ident.public_bytes().hex() == _SEED_PUB_HEX


def test_identity_from_seed_rejects_wrong_length() -> None:
    import pytest

    with pytest.raises(ValueError, match="32 bytes"):
        Identity.from_seed(b"too-short")


def test_identity_generate_produces_unique_keys() -> None:
    a = Identity.generate()
    b = Identity.generate()
    assert a.key_id != b.key_id
    assert a.public_bytes() != b.public_bytes()


def test_identity_key_id_matches_content_digest_formula() -> None:
    ident = Identity.generate()
    expected = content_digest({"ed25519_pub_b64": b64encode(ident.public_bytes())})
    assert ident.key_id == expected


def test_identity_sign_and_verify_roundtrip() -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    ident = Identity.generate()
    msg = b"hello ironclad"
    sig = ident.sign(msg)
    assert len(sig) == 64
    Ed25519PublicKey.from_public_bytes(ident.public_bytes()).verify(sig, msg)


# --- Evidence wire-format pinning ---


def test_evidence_digest_matches_vector() -> None:
    e = Evidence(
        predicate="aafp.commons:packet:signed",
        subject="pkt-123",
        timestamp=1000000.0,
        data={"ns": "commons/test"},
        observer="key-abc",
        nonce=_EV_NONCE,
    )
    assert e.digest() == _EV_DIGEST


def test_evidence_signing_payload_matches_vector() -> None:
    e = Evidence(
        predicate="aafp.commons:packet:signed",
        subject="pkt-123",
        timestamp=1000000.0,
        data={"ns": "commons/test"},
        observer="key-abc",
        nonce=_EV_NONCE,
    )
    assert e.signing_payload().hex() == _EV_SP_HEX


def test_evidence_nonce_auto_generated() -> None:
    e = Evidence(
        predicate="p", subject="s", timestamp=1.0, data={}, observer="o"
    )
    assert len(e.nonce) == 22  # secrets.token_urlsafe(16) → 22 chars


def test_evidence_is_frozen() -> None:
    e = Evidence(predicate="p", subject="s", timestamp=1.0, data={}, observer="o")
    import dataclasses

    assert dataclasses.is_dataclass(e)
    try:
        e.predicate = "x"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("Evidence should be frozen")


# --- Receipt wire-format pinning ---


def _make_test_evidence() -> Evidence:
    return Evidence(
        predicate="aafp.commons:packet:signed",
        subject="pkt-123",
        timestamp=1000000.0,
        data={"ns": "commons/test"},
        observer="key-abc",
        nonce=_EV_NONCE,
    )


def test_receipt_digest_with_previous_matches_vector() -> None:
    r = Receipt(
        evidence=_make_test_evidence(),
        signature_b64="sigABC",
        previous_receipt_digest="prevDEF",
    )
    assert r.receipt_digest == _RC_DIGEST


def test_receipt_digest_without_previous_matches_vector() -> None:
    r = Receipt(
        evidence=_make_test_evidence(),
        signature_b64="sigABC",
        previous_receipt_digest=None,
    )
    assert r.receipt_digest == _RC_DIGEST_NONE


def test_receipt_digest_excludes_timestamp() -> None:
    """receipt_digest must not change when only the evidence timestamp changes."""
    e1 = _make_test_evidence()
    e2 = Evidence(
        predicate=e1.predicate,
        subject=e1.subject,
        timestamp=9999999.0,
        data=e1.data,
        observer=e1.observer,
        nonce=e1.nonce,
    )
    r1 = Receipt(evidence=e1, signature_b64="sig", previous_receipt_digest=None)
    r2 = Receipt(evidence=e2, signature_b64="sig", previous_receipt_digest=None)
    assert r1.receipt_digest == r2.receipt_digest


def test_receipt_chain_links_via_previous_digest() -> None:
    e1 = Evidence(predicate="p", subject="s1", timestamp=1.0, data={}, observer="o")
    r1 = Receipt(evidence=e1, signature_b64="sig1", previous_receipt_digest=None)
    e2 = Evidence(predicate="p", subject="s2", timestamp=2.0, data={}, observer="o")
    r2 = Receipt(evidence=e2, signature_b64="sig2", previous_receipt_digest=r1.receipt_digest)
    assert r2.previous_receipt_digest == r1.receipt_digest
    assert r1.receipt_digest != r2.receipt_digest


# --- Full sign → verify → tamper round-trip via aafp_commons ---


def _make_packet() -> KnowledgePacket:
    return KnowledgePacket(
        kind="finding",
        namespace="commons/test/r2",
        claim="Vendored ironclad preserves the wire format.",
        scope={"area": "signing"},
        evidence=(
            EvidenceRef(
                kind="reproduction",
                uri="artifact://tests/r2-1",
                observed_at=int(time.time()),
            ),
        ),
        confidence=0.9,
        author_agent_id=derive_agent_id(b"fixture-r2-agent-public-key"),
        constitution=ConstitutionRef("test-r2", "1.0"),
        method=MethodRef("r2-compat", "1.0"),
    )


def test_signed_packet_roundtrip_with_vendored_ironclad() -> None:
    ident = Identity.generate()
    signed = sign_packet(_make_packet(), ident)
    assert signed.signer_key_id == ident.key_id
    assert signed.scheme == "ironclad-ed25519-v1"
    assert signed.verify()


def test_signed_packet_tampering_fails_closed() -> None:
    ident = Identity.generate()
    data = sign_packet(_make_packet(), ident).to_dict()
    data["packet"]["claim"] = "Tampered after signing."
    tampered = SignedPacket.from_dict(data)
    assert not tampered.verify()


def test_signed_packet_receipt_tampering_fails_closed() -> None:
    from copy import deepcopy

    ident = Identity.generate()
    data = deepcopy(sign_packet(_make_packet(), ident).to_dict())
    data["receipt"]["evidence"]["data"]["namespace"] = "commons/poisoned"
    tampered = SignedPacket.from_dict(data)
    assert not tampered.verify()


def test_signed_packet_chain_with_previous_receipt_digest() -> None:
    ident = Identity.generate()
    first = sign_packet(_make_packet(), ident)
    second = sign_packet(
        _make_packet(), ident, previous_receipt_digest=first.receipt["receipt_digest"]
    )
    assert second.receipt["previous_receipt_digest"] == first.receipt["receipt_digest"]
    assert first.receipt["receipt_digest"] != second.receipt["receipt_digest"]
    assert first.verify()
    assert second.verify()


# --- Ledger round-trip ---


def test_ledger_roundtrip_with_vendored_ironclad(tmp_path: Path) -> None:
    ident = Identity.generate()
    ledger = Ledger(tmp_path / "ledger.jsonl")
    first = ledger.append(("sha256:" + "1" * 64,), ident)
    second = ledger.append(("sha256:" + "2" * 64, "sha256:" + "3" * 64), ident)
    result = ledger.verify()
    assert result.valid
    assert result.blocks == 2
    assert result.packets == 3
    assert second.block.previous_hash == first.block.block_hash
    assert first.scheme == "ironclad-ed25519-v1"


def test_ledger_tampering_detected_with_vendored_ironclad(tmp_path: Path) -> None:
    import json

    ident = Identity.generate()
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger(path)
    ledger.append(("sha256:" + "1" * 64,), ident)
    data = json.loads(path.read_text())
    data["block"]["packet_digests"] = ["sha256:" + "9" * 64]
    path.write_text(json.dumps(data) + "\n")
    assert not ledger.verify().valid


# --- Module resolution: vendored, not external ---


def test_ironclad_resolves_to_vendored_package() -> None:
    import ironclad

    assert "src/ironclad" in ironclad.__file__
    assert "/Users/david/Projects/ironclad" not in ironclad.__file__
