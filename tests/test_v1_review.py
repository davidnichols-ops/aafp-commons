import json
from dataclasses import replace
from pathlib import Path

from jsonschema import validate

from aafp_commons.repository import CommonsRepository
from aafp_commons.review import decide, queue
from aafp_commons.signing import sign_packet
from aafp_commons.w1 import world


def _repo(tmp_path, packet, identity, constitution):
    repo = CommonsRepository(tmp_path)
    repo.install_constitution(constitution)
    assert repo.submit(sign_packet(packet, identity), identity).accepted
    return repo


def test_admitted_claim_is_queued_and_review_result_matches_schema(
    tmp_path, packet, identity, constitution
):
    constitution = replace(constitution, namespace_prefixes=("commons/frontend", "commons/review"))
    packet = replace(packet, constitution=constitution.ref)
    repo = _repo(tmp_path, packet, identity, constitution)
    queued = queue(repo, packet.packet_id)
    assert queued["state"] == "in-review"
    result = decide(repo, packet.packet_id, identity, constitution, "need-evidence")
    review = repo.get(result["review_id"])
    schema = json.loads(
        Path(__file__).parents[1].joinpath("protocols/review-result@1.schema.json").read_text()
    )
    validate(review.packet.scope, schema)
    assert review.packet.kind == "finding"
    assert review.packet.namespace == "commons/review/result"
    assert result["independent"] is True
    assert queue(repo, packet.packet_id)["state"] == "complete"


def test_world_projects_unreviewed_claim(tmp_path, packet, identity, constitution):
    repo = _repo(tmp_path, packet, identity, constitution)
    projection = world(tmp_path)
    assert projection["review_queue"][0]["claim_id"] == packet.packet_id
    assert projection["review_queue"][0]["state"] == "in-review"
    del repo
