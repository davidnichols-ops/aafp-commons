from dataclasses import replace

from aafp_commons.conflicts import resolve
from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import sign_packet
from aafp_commons.verification import record_verification, status


def test_resolution_requires_explicit_trusted_policy(tmp_path, packet, identity, constitution):
    constitution = replace(constitution, namespace_prefixes=("commons",))
    packet = replace(packet, constitution=constitution.ref)
    repo = CommonsRepository(tmp_path)
    repo.install_constitution(constitution)
    assert repo.submit(sign_packet(packet, identity), identity).accepted
    first = record_verification(tmp_path, packet.packet_id, "m", "a", "supported", identity)
    record_verification(tmp_path, packet.packet_id, "m", "b", "failed", identity)
    resolution = resolve(
        repo, packet.packet_id, identity, constitution,
        first["verification_id"], "prefer a",
    )
    value = status(repo, packet.packet_id)
    assert value["supported"] is False
    assert value["rely_ok"] is False
    resolver = repo.get(resolution["resolution_id"]).packet.author_agent_id
    policy = {
        "mode": "consequential", "accept_resolution": True,
        "accepted_decisions": ["prefer-a", "prefer-b"],
        "trusted_resolvers": [resolver], "trusted_verifiers": [],
        "allow_same_operator_resolve": True,
    }
    value = status(repo, packet.packet_id, policy)
    assert value["rely_ok"] is True
    assert value["supported"] is False
