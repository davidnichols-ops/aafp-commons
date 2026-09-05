from __future__ import annotations

import pytest
from ironclad.trust import Identity

from aafp_commons.publication import PublicationService
from aafp_commons.sharing import SNAPSHOT_SCHEMA
from aafp_commons.signing import sign_packet


def test_publish_records_publisher_separately(packet, identity) -> None:  # type: ignore[no-untyped-def]
    signed = sign_packet(packet, identity)
    service = PublicationService()
    snapshot = {"schema": SNAPSHOT_SCHEMA, "packets": [signed.to_dict()],
                "constitutions": [], "count": 1}
    publisher = Identity.generate()
    record = service.publish(snapshot, publisher)
    assert record["publisher_id"] == publisher.key_id
    assert record["publisher_id"] != signed.signer_key_id
    assert service.stats()["publications"] == 1


def test_publish_rejects_unauthorized_snapshot(packet, identity) -> None:  # type: ignore[no-untyped-def]
    signed = sign_packet(packet, identity)
    snapshot = {"schema": SNAPSHOT_SCHEMA, "packets": [signed.to_dict()],
                "constitutions": [], "count": 1}
    with pytest.raises(PermissionError):
        PublicationService().publish(snapshot, Identity.generate(), lambda *_: False)


def test_revoked_publisher_and_rate_limit_fail_closed(packet, identity) -> None:  # type: ignore[no-untyped-def]
    signed = sign_packet(packet, identity)
    snapshot = {"schema": SNAPSHOT_SCHEMA, "packets": [signed.to_dict()],
                "constitutions": [], "count": 1}
    service = PublicationService(max_publications_per_publisher=1)
    service.publish(snapshot, identity)
    with pytest.raises(PermissionError, match="limit"):
        service.publish(snapshot, identity)
    other = Identity.generate()
    assert not service.is_publisher_revoked(other.key_id)
    service.revoke_publisher(other.key_id)
    assert service.is_publisher_revoked(other.key_id)
    assert service.stats()["revoked_publishers"] == 1
    with pytest.raises(PermissionError, match="revoked"):
        service.publish(snapshot, other)


def test_privacy_policy_runs_before_publication(packet, identity) -> None:  # type: ignore[no-untyped-def]
    signed = sign_packet(packet, identity)
    snapshot = {"schema": SNAPSHOT_SCHEMA, "packets": [signed.to_dict()],
                "constitutions": [], "count": 1}
    with pytest.raises(PermissionError, match="privacy"):
        PublicationService().publish(snapshot, identity, privacy_policy=lambda _: False)


def test_publication_listing_is_deterministic(packet, identity) -> None:  # type: ignore[no-untyped-def]
    signed = sign_packet(packet, identity)
    snapshot = {"schema": SNAPSHOT_SCHEMA, "packets": [signed.to_dict()],
                "constitutions": [], "count": 1}
    service = PublicationService()
    service.publish(snapshot, identity)
    assert service.publications() == sorted(service.publications(),
                                           key=lambda item: item["publication_id"])
    with pytest.raises(ValueError, match="limit"):
        service.publications(limit=0)


def test_publication_state_survives_restart(tmp_path, packet, identity) -> None:  # type: ignore[no-untyped-def]
    signed = sign_packet(packet, identity)
    snapshot = {"schema": SNAPSHOT_SCHEMA, "packets": [signed.to_dict()],
                "constitutions": [], "count": 1}
    service = PublicationService(max_publications_per_publisher=2)
    service.publish(snapshot, identity)
    service.revoke_publisher("revoked-key")
    service.save(tmp_path)
    restored = PublicationService.load(tmp_path)
    assert restored.publications() == service.publications()
    assert restored.is_publisher_revoked("revoked-key")
    assert restored.stats() == service.stats()


def test_publication_state_rejects_malformed_records(tmp_path, packet, identity) -> None:  # type: ignore[no-untyped-def]
    service = PublicationService()
    service.save(tmp_path)
    state_path = tmp_path / "service.json"
    state = __import__("json").loads(state_path.read_text())
    state["publications"] = [{"schema": "wrong"}]
    state_path.write_text(__import__("json").dumps(state))
    with pytest.raises(ValueError, match="records"):
        PublicationService.load(tmp_path)


def test_publication_state_rejects_invalid_counter(tmp_path) -> None:
    service = PublicationService(max_publications_per_publisher=2)
    service.save(tmp_path)
    state_path = tmp_path / "service.json"
    state = __import__("json").loads(state_path.read_text())
    state["publisher_counts"] = {"key": 3}
    state_path.write_text(__import__("json").dumps(state))
    with pytest.raises(ValueError, match="counters"):
        PublicationService.load(tmp_path)


def test_publication_state_rejects_counter_record_mismatch(tmp_path, packet, identity) -> None:  # type: ignore[no-untyped-def]
    signed = sign_packet(packet, identity)
    snapshot = {"schema": SNAPSHOT_SCHEMA, "packets": [signed.to_dict()],
                "constitutions": [], "count": 1}
    service = PublicationService()
    service.publish(snapshot, identity)
    service.save(tmp_path)
    path = tmp_path / "service.json"
    state = __import__("json").loads(path.read_text())
    state["publisher_counts"] = {}
    path.write_text(__import__("json").dumps(state))
    with pytest.raises(ValueError, match="match"):
        PublicationService.load(tmp_path)


def test_sync_from_peer_applies_missing_delta(packet, identity) -> None:  # type: ignore[no-untyped-def]
    signed = sign_packet(packet, identity)
    snapshot = {"schema": SNAPSHOT_SCHEMA, "packets": [signed.to_dict()],
                "constitutions": [], "count": 1}
    source = PublicationService()
    target = PublicationService()
    source.index.ingest(snapshot)
    assert target.sync_from_peer(source.checkpoint(), source.index.export_delta) == 1
    assert target.checkpoint() == source.checkpoint()
    assert target.sync_from_peer(source.checkpoint(), source.index.export_delta) == 0
