from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aafp_commons.index import PublicResearchIndex
from aafp_commons.repository import CommonsRepository
from aafp_commons.sharing import SNAPSHOT_SCHEMA, export_public_snapshot
from aafp_commons.signing import sign_packet


def test_public_research_index_ingests_and_deduplicates_empty_snapshots() -> None:
    index = PublicResearchIndex()
    snapshot = {"schema": SNAPSHOT_SCHEMA, "packets": [], "constitutions": [], "count": 0}
    assert index.ingest(snapshot) == 0
    assert index.ingest(snapshot) == 0
    assert len(index) == 0
    assert index.search("anything") == []
    assert index.get_constitution("grok-truth-seeking", "1.0.0") is None
    assert index.list_constitutions() == []
    assert index.stats() == {"packet_count": 0, "constitution_count": 0, "max_packets": 100_000}
    results = index.search("anything")
    assert results == []


def test_public_research_index_retains_manifest_metadata(
    tmp_path, packet, constitution, identity
) -> None:
    repository = CommonsRepository(tmp_path / "node")
    repository.install_constitution(constitution)
    repository.submit(sign_packet(packet, identity), identity)
    snapshot = export_public_snapshot(repository, tmp_path / "snapshot.json")
    index = PublicResearchIndex()
    assert index.ingest(snapshot) == 1
    assert index.get_constitution("frontier-dev", "0.1") is not None


def test_public_research_index_persists_empty_index(tmp_path) -> None:
    index = PublicResearchIndex()
    path = tmp_path / "index.json"
    index.save(path)
    restored = PublicResearchIndex.load(path)
    assert len(restored) == 0
    assert restored.max_packets == 100_000
    schema = json.loads(
        (Path(__file__).parents[1] / "protocols" / "research-index@1.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(json.loads(path.read_text()))


def test_public_research_index_rejects_tampered_count(tmp_path) -> None:
    path = tmp_path / "index.json"
    path.write_text(json.dumps({
        "schema": "aafp.commons/research-index@1", "packets": [], "count": 1,
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="count"):
        PublicResearchIndex.load(path)


def test_public_research_index_rejects_invalid_limits() -> None:
    import pytest
    with pytest.raises(ValueError, match="max_packets"):
        PublicResearchIndex(max_packets=0)


def test_public_research_index_enforces_cumulative_limit() -> None:
    index = PublicResearchIndex(max_packets=1)
    snapshot = {"schema": SNAPSHOT_SCHEMA, "packets": [], "constitutions": [], "count": 0}
    assert index.ingest(snapshot) == 0


def test_public_research_index_rejects_invalid_search_limit() -> None:
    import pytest
    with pytest.raises(ValueError, match="limit"):
        PublicResearchIndex().search("anything", limit=0)


def test_checkpoint_is_deterministic(packet, identity) -> None:  # type: ignore[no-untyped-def]
    signed = sign_packet(packet, identity)
    snapshot = {"schema": SNAPSHOT_SCHEMA, "packets": [signed.to_dict()],
                "constitutions": [], "count": 1}
    first = PublicResearchIndex()
    second = PublicResearchIndex()
    first.ingest(snapshot)
    second.ingest(snapshot)
    assert first.checkpoint() == second.checkpoint()
    assert first.checkpoint()["schema"] == "aafp.commons/research-checkpoint@1"
    assert second.missing_from_checkpoint(first.checkpoint()) == []
    altered = dict(first.checkpoint(), packet_ids=first.checkpoint()["packet_ids"] + ["missing"])
    altered["packet_count"] = 2
    from ironclad.canon import content_digest
    altered["digest"] = content_digest({"packets": sorted(altered["packet_ids"]),
                                         "constitutions": []})
    assert second.missing_from_checkpoint(altered) == ["missing"]
    with pytest.raises(ValueError, match="digest"):
        second.missing_from_checkpoint(dict(altered, digest="bad"))


def test_delta_export_and_apply_is_idempotent(packet, identity) -> None:  # type: ignore[no-untyped-def]
    signed = sign_packet(packet, identity)
    snapshot = {"schema": SNAPSHOT_SCHEMA, "packets": [signed.to_dict()],
                "constitutions": [], "count": 1}
    source = PublicResearchIndex()
    target = PublicResearchIndex()
    source.ingest(snapshot)
    delta = source.export_delta([signed.packet_id])
    assert delta["schema"] == "aafp.commons/research-delta@1"
    assert target.apply_delta(delta) == 1
    assert target.apply_delta(delta) == 0
    assert target.checkpoint() == source.checkpoint()
