from aafp_commons.verification import status


def test_status_does_not_infer_support_from_repetition(tmp_path, packet, identity, constitution):
    from aafp_commons.repository import CommonsRepository
    from aafp_commons.signing import sign_packet

    repo = CommonsRepository(tmp_path)
    repo.install_constitution(constitution)
    assert repo.submit(sign_packet(packet, identity), identity).accepted
    assert status(repo, packet.packet_id)["supported"] is False
