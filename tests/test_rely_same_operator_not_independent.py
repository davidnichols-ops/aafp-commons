"""G-RELY: same-operator verification is not independent corroboration."""

from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import sign_packet
from aafp_commons.verification import record_verification, rely


def test_same_operator_reproduced_rejected_for_consequential(
    tmp_path, packet, identity, constitution
):
    repo = CommonsRepository(tmp_path)
    repo.install_constitution(constitution)
    assert repo.submit(sign_packet(packet, identity), identity).accepted

    # Verifier uses the same agent ID as the publisher — not independent.
    record_verification(
        tmp_path, packet.packet_id, "method-1",
        packet.author_agent_id, "reproduced", identity,
    )

    decision = rely(repo, packet.packet_id)
    assert decision["display"] is True
    assert decision["consequential"] is False
    assert decision["status"]["independent_corroboration"] is False


def test_same_operator_allowed_when_policy_permits(
    tmp_path, packet, identity, constitution
):
    repo = CommonsRepository(tmp_path)
    repo.install_constitution(constitution)
    assert repo.submit(sign_packet(packet, identity), identity).accepted

    (tmp_path / "policy.rely.json").write_text(
        '{"trusted_verifiers": ["' + packet.author_agent_id + '"], '
        '"allow_same_operator": true}'
    )

    record_verification(
        tmp_path, packet.packet_id, "method-1",
        packet.author_agent_id, "reproduced", identity,
    )

    decision = rely(repo, packet.packet_id)
    assert decision["consequential"] is True
