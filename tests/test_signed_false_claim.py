from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import sign_packet
from aafp_commons.verification import status


def test_admitted_claim_is_not_supported_by_signature(tmp_path, packet, identity, constitution):
    repo = CommonsRepository(tmp_path)
    repo.install_constitution(constitution)
    assert repo.submit(sign_packet(packet, identity), identity).accepted
    value = status(repo, packet.packet_id)
    assert value["evidence_supplied"] is True
    assert value["digest_checked"] is False
    assert value["supported"] is False
