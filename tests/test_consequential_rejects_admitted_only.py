"""G-RELY: consequential rejects admitted-only claims (evidence but no reproduction)."""

from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import sign_packet
from aafp_commons.verification import rely


def test_admitted_only_rejected_at_consequential(
    tmp_path, packet, identity, constitution
):
    repo = CommonsRepository(tmp_path)
    repo.install_constitution(constitution)
    assert repo.submit(sign_packet(packet, identity), identity).accepted

    # No verification results recorded — claim is admitted but not reproduced.
    decision = rely(repo, packet.packet_id)
    assert decision["display"] is True
    assert decision["consequential"] is False
    assert decision["status"]["evidence_supplied"] is True
    assert decision["status"]["reproduced"] is False
    assert decision["status"]["supported"] is False
    assert decision["status"]["rely_ok"] is False


def test_unsigned_reproduced_does_not_satisfy_consequential(
    tmp_path, packet, identity, constitution
):
    from aafp_commons.verification import record_verification

    repo = CommonsRepository(tmp_path)
    repo.install_constitution(constitution)
    assert repo.submit(sign_packet(packet, identity), identity).accepted

    # Unsigned reproduction — no signature, so not trusted.
    record_verification(
        tmp_path, packet.packet_id, "method-1",
        "aafp:different-verifier", "reproduced",
    )

    decision = rely(repo, packet.packet_id)
    assert decision["consequential"] is False
    assert decision["status"]["verifier_signed"] is False
