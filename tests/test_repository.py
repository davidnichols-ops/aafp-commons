from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from ironclad.trust import Identity

from aafp_commons.constitutions import ConstitutionManifest
from aafp_commons.models import KnowledgePacket
from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import sign_packet


def test_submit_query_and_verify(
    tmp_path: Path,
    packet: KnowledgePacket,
    identity: Identity,
    constitution: ConstitutionManifest,
) -> None:
    repository = CommonsRepository(tmp_path)
    repository.install_constitution(constitution)
    decision = repository.submit(sign_packet(packet, identity), identity)
    assert decision.accepted
    assert decision.status == "admissible"
    assert repository.get(packet.packet_id).packet == packet
    assert repository.query("commons/frontend")
    assert repository.verify().valid


def test_duplicate_submission_is_idempotent(
    tmp_path: Path,
    packet: KnowledgePacket,
    identity: Identity,
    constitution: ConstitutionManifest,
) -> None:
    repository = CommonsRepository(tmp_path)
    repository.install_constitution(constitution)
    signed = sign_packet(packet, identity)
    repository.submit(signed, identity)
    second = repository.submit(signed, identity)
    assert second.status == "already-present"
    assert repository.verify().ledger.blocks == 1


def test_policy_rejects_apparent_secret(
    tmp_path: Path,
    packet: KnowledgePacket,
    identity: Identity,
    constitution: ConstitutionManifest,
) -> None:
    poisoned = replace(
        packet,
        claim="Observed api_key=sk-this-should-never-be-published in agent output.",
    )
    repository = CommonsRepository(tmp_path)
    repository.install_constitution(constitution)
    decision = repository.submit(sign_packet(poisoned, identity), identity)
    assert not decision.accepted
    assert "secret material" in decision.reasons[0]


def test_missing_object_breaks_repository_verification(
    tmp_path: Path,
    packet: KnowledgePacket,
    identity: Identity,
    constitution: ConstitutionManifest,
) -> None:
    repository = CommonsRepository(tmp_path)
    repository.install_constitution(constitution)
    repository.submit(sign_packet(packet, identity), identity)
    repository.object_path(packet.packet_id).unlink()
    result = repository.verify()
    assert not result.valid
    assert any("missing object" in error for error in result.errors)


def test_object_tampering_breaks_repository_verification(
    tmp_path: Path,
    packet: KnowledgePacket,
    identity: Identity,
    constitution: ConstitutionManifest,
) -> None:
    repository = CommonsRepository(tmp_path)
    repository.install_constitution(constitution)
    repository.submit(sign_packet(packet, identity), identity)
    path = repository.object_path(packet.packet_id)
    data = json.loads(path.read_text())
    data["packet"]["confidence"] = 0.99
    path.write_text(json.dumps(data))
    assert not repository.verify().valid
