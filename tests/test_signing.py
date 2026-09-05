from __future__ import annotations

from copy import deepcopy

from ironclad.trust import Identity

from aafp_commons.models import KnowledgePacket
from aafp_commons.signing import SignedPacket, sign_packet


def test_ironclad_packet_signature_and_receipt_verify(
    packet: KnowledgePacket, identity: Identity
) -> None:
    signed = sign_packet(packet, identity)
    assert signed.signer_key_id == identity.key_id
    assert signed.verify()


def test_packet_tampering_fails_closed(packet: KnowledgePacket, identity: Identity) -> None:
    data = sign_packet(packet, identity).to_dict()
    data["packet"]["claim"] = "This packet was tampered with after signing."
    tampered = SignedPacket.from_dict(data)
    assert not tampered.verify()


def test_receipt_tampering_fails_closed(packet: KnowledgePacket, identity: Identity) -> None:
    data = deepcopy(sign_packet(packet, identity).to_dict())
    data["receipt"]["evidence"]["data"]["namespace"] = "commons/poisoned"
    tampered = SignedPacket.from_dict(data)
    assert not tampered.verify()

