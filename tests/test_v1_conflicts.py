import json
from dataclasses import replace
from pathlib import Path

from jsonschema import validate

from aafp_commons.conflicts import resolve
from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import sign_packet
from aafp_commons.verification import record_verification, status


def test_conflicting_signed_results_remain_visible_and_resolution_is_append_only(
    tmp_path, packet, identity, constitution
):
    constitution = replace(constitution, namespace_prefixes=("commons",))
    packet = replace(packet, constitution=constitution.ref)
    repo = CommonsRepository(tmp_path)
    repo.install_constitution(constitution)
    assert repo.submit(sign_packet(packet, identity), identity).accepted
    first = record_verification(tmp_path, packet.packet_id, "method", "a", "supported", identity)
    second = record_verification(tmp_path, packet.packet_id, "method", "b", "failed", identity)
    before = status(repo, packet.packet_id)
    assert before["conflict"] is True
    assert before["rely_ok"] is False
    assert set(before["conflict_digests"]) == {first["verification_id"], second["verification_id"]}
    result = resolve(
        repo, packet.packet_id, identity, constitution,
        first["verification_id"], "method A is preferred",
    )
    after = status(repo, packet.packet_id)
    assert result["resolution_id"] in after["resolution_digests"]
    assert after["conflict"] is True
    assert after["rely_ok"] is False
    resolution = repo.get(result["resolution_id"])
    schema = json.loads(Path("protocols/review-resolution@1.schema.json").read_text())
    validate(resolution.packet.scope, schema)
