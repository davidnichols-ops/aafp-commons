from __future__ import annotations

from dataclasses import replace

import pytest

from aafp_commons.identity import derive_agent_id
from aafp_commons.models import KnowledgePacket


def test_packet_round_trip_is_content_address_stable(packet: KnowledgePacket) -> None:
    rebuilt = KnowledgePacket.from_dict(packet.to_dict())
    assert rebuilt == packet
    assert rebuilt.packet_id == packet.packet_id


def test_packet_rejects_invalid_namespace(packet: KnowledgePacket) -> None:
    with pytest.raises(ValueError, match="namespace"):
        replace(packet, namespace="protocol/root")


def test_packet_rejects_invalid_confidence(packet: KnowledgePacket) -> None:
    with pytest.raises(ValueError, match="confidence"):
        replace(packet, confidence=1.1)


def test_agent_id_derivation_matches_sha256_shape() -> None:
    agent_id = derive_agent_id(b"public-key")
    assert agent_id.startswith("aafp:")
    assert len(agent_id) == 69

