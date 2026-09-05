from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from aafp_commons import (
    ADOPTION_BOUNDARY,
    AdoptionRequestError,
    CommonsRepository,
    ConstitutionAdoptionRequest,
    ConstitutionCatalog,
    ConstitutionRef,
    FileAdoptionRequestStore,
    default_registry,
    derive_agent_id,
)


def _installed_catalog(root: Path) -> ConstitutionCatalog:
    repository = CommonsRepository(root)
    for package in default_registry().list():
        repository.install_constitution(package.manifest)
    return ConstitutionCatalog(repository.constitutions)


def test_agent_requests_exact_compatible_constitution(tmp_path: Path) -> None:
    agent_id = derive_agent_id(b"requesting-agent")
    result = _installed_catalog(tmp_path).request_adoption(
        requester_agent_id=agent_id,
        runtime="grok",
        namespace="commons/frontend/react",
        packet_kind="finding",
        purpose="Share reproducible frontend findings.",
        created_at=1_725_000_000,
    )
    assert result is not None
    request, manifest = result
    assert request.requester_agent_id == agent_id
    assert request.constitution == manifest.ref
    assert request.constitution.digest == manifest.manifest_digest
    assert request.status == "awaiting-runtime-acceptance"
    assert request.provider_constraint_policy == "preserve"
    assert request.request_id.startswith("sha256:")
    assert "May agent" in request.question
    assert "does not prove AAFP identity" in ADOPTION_BOUNDARY


def test_adoption_request_id_covers_every_field(tmp_path: Path) -> None:
    result = _installed_catalog(tmp_path).request_adoption(
        requester_agent_id=derive_agent_id(b"requesting-agent"),
        runtime="claude",
        namespace="commons/research",
        packet_kind="observation",
        created_at=123,
    )
    assert result is not None
    request, _ = result
    assert replace(request, purpose="different").request_id != request.request_id
    assert replace(request, created_at=124).request_id != request.request_id


def test_adoption_request_requires_digest_pin() -> None:
    with pytest.raises(ValueError, match="pin an exact sha256 constitution digest"):
        ConstitutionAdoptionRequest(
            requester_agent_id=derive_agent_id(b"requester"),
            runtime="custom",
            namespace="commons/research",
            packet_kind="finding",
            constitution=ConstitutionRef("example", "1.0.0"),
        )


def test_adoption_request_cannot_drop_provider_constraints() -> None:
    with pytest.raises(ValueError, match="preserve provider constraints"):
        ConstitutionAdoptionRequest(
            requester_agent_id=derive_agent_id(b"requester"),
            runtime="custom",
            namespace="commons/research",
            packet_kind="finding",
            constitution=ConstitutionRef("example", "1.0.0", "sha256:" + "a" * 64),
            provider_constraint_policy="replace",  # type: ignore[arg-type]
        )


def test_request_returns_none_without_guided_match(tmp_path: Path) -> None:
    assert _installed_catalog(tmp_path).request_adoption(
        requester_agent_id=derive_agent_id(b"requester"),
        runtime="unknown-runtime",
        namespace="commons/research",
        packet_kind="finding",
    ) is None


def test_request_store_is_idempotent_and_content_addressed(tmp_path: Path) -> None:
    catalog = _installed_catalog(tmp_path)
    result = catalog.request_adoption(
        requester_agent_id=derive_agent_id(b"requester"),
        runtime="claude",
        namespace="commons/research",
        packet_kind="finding",
        created_at=456,
    )
    assert result is not None
    request, _ = result
    repository = CommonsRepository(tmp_path)
    first = repository.record_adoption_request(request)
    second = repository.record_adoption_request(request)
    assert first == second == request.request_id
    assert repository.adoption_requests.get(first) == request
    assert repository.adoption_requests.list() == [request]
    assert not (tmp_path / "ledger.jsonl").exists()


def test_request_store_rejects_tampered_file(tmp_path: Path) -> None:
    store = FileAdoptionRequestStore(tmp_path / "requests")
    request_id = "sha256:" + "a" * 64
    path = store.request_path(request_id)
    path.parent.mkdir(parents=True)
    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid adoption request"):
        store.get(request_id)


def test_runtime_acceptance_activates_exact_guidance(tmp_path: Path) -> None:
    result = _installed_catalog(tmp_path).request_adoption(
        requester_agent_id=derive_agent_id(b"agent"),
        runtime="codex",
        namespace="commons/frontend/react",
        packet_kind="finding",
        created_at=10,
    )
    assert result is not None
    request, manifest = result
    repository = CommonsRepository(tmp_path)
    repository.record_adoption_request(request)
    decision = repository.respond_to_adoption_request(
        request.request_id,
        accepted=True,
        decided_at=11,
    )
    assert decision.accepted
    assert decision.status == "accepted"
    assert decision.constitution == request.constitution
    assert decision.decision_id.startswith("sha256:")
    assert repository.resolve_adopted_constitution(request.request_id) == manifest
    assert not (tmp_path / "ledger.jsonl").exists()


def test_runtime_rejection_does_not_activate_guidance(tmp_path: Path) -> None:
    result = _installed_catalog(tmp_path).request_adoption(
        requester_agent_id=derive_agent_id(b"agent"),
        runtime="grok",
        namespace="commons/research",
        packet_kind="observation",
        created_at=10,
    )
    assert result is not None
    request, _ = result
    repository = CommonsRepository(tmp_path)
    repository.record_adoption_request(request)
    decision = repository.respond_to_adoption_request(
        request.request_id,
        accepted=False,
        reason="Runtime operator policy declined optional guidance.",
        decided_at=11,
    )
    assert decision.status == "rejected"
    with pytest.raises(AdoptionRequestError, match="rejected"):
        repository.resolve_adopted_constitution(request.request_id)


def test_runtime_decision_is_immutable(tmp_path: Path) -> None:
    result = _installed_catalog(tmp_path).request_adoption(
        requester_agent_id=derive_agent_id(b"agent"),
        runtime="claude",
        namespace="commons/research",
        packet_kind="finding",
        created_at=10,
    )
    assert result is not None
    request, _ = result
    repository = CommonsRepository(tmp_path)
    repository.record_adoption_request(request)
    repository.respond_to_adoption_request(
        request.request_id, accepted=True, decided_at=11
    )
    with pytest.raises(ValueError, match="different immutable decision"):
        repository.respond_to_adoption_request(
            request.request_id,
            accepted=False,
            reason="Changed mind.",
            decided_at=12,
        )


def test_runtime_decision_file_is_content_addressed(tmp_path: Path) -> None:
    result = _installed_catalog(tmp_path).request_adoption(
        requester_agent_id=derive_agent_id(b"agent"),
        runtime="codex",
        namespace="commons/research",
        packet_kind="finding",
        created_at=10,
    )
    assert result is not None
    request, _ = result
    repository = CommonsRepository(tmp_path)
    repository.record_adoption_request(request)
    decision = repository.respond_to_adoption_request(
        request.request_id, accepted=True, decided_at=11
    )
    path = repository.adoption_decisions.decision_path(
        request.request_id, decision.decision_id
    )
    assert path.exists()
    value = path.read_text(encoding="utf-8").replace(
        '"reason": ""', '"reason": "tampered"'
    )
    path.write_text(value, encoding="utf-8")
    with pytest.raises(ValueError, match="content address"):
        repository.adoption_decisions.get(request.request_id)
