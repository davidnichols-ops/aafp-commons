from __future__ import annotations

from pathlib import Path

from aafp_commons import (
    AgentJoinSession,
    CommonsRepository,
    ConstitutionRef,
    RuntimeHandshake,
    default_registry,
)
from aafp_commons.identity import derive_agent_id


def test_join_session_composes_handshake_adoption_and_context(tmp_path: Path) -> None:
    repository = CommonsRepository(tmp_path)
    package = default_registry().get("grok-truth-seeking")
    repository.install_constitution(package.manifest)
    session = AgentJoinSession.begin(
        repository,
        RuntimeHandshake(
            runtime="grok",
            runtime_version="3",
            identity_convention="runtime-native",
            identity_hint="session",
            declared_at=1,
        ),
        agent_id=derive_agent_id(b"join-agent"),
        namespace="commons/research",
        packet_kind="finding",
        constitution="grok-truth-seeking@1.0.0",
        created_at=2,
    )
    assert session.state == "awaiting-runtime-acceptance"
    assert repository.ledger.blocks() == []


def test_join_session_prefers_handshake_accepted_constitution(tmp_path: Path) -> None:
    repository = CommonsRepository(tmp_path)
    packages = default_registry()
    for package in packages.list():
        repository.install_constitution(package.manifest)
    selected = packages.get("gpt-astra-6").manifest.ref
    session = AgentJoinSession.begin(
        repository,
        RuntimeHandshake(
            runtime="codex",
            runtime_version="1",
            identity_convention="runtime-native",
            identity_hint="session",
            accepted_constitutions=(ConstitutionRef(
                selected.constitution_id, selected.version, selected.digest
            ),),
            declared_at=1,
        ),
        agent_id=derive_agent_id(b"preference-agent"),
        namespace="commons/research",
        packet_kind="finding",
        created_at=2,
    )
    assert session.request.constitution.constitution_id == "gpt-astra-6"
    accepted = session.accept(decided_at=3)
    context = accepted.working_context()
    assert accepted.state == "accepted"
    assert context["active"] is True
    assert context["handshake_id"] == session.handshake_id
    assert repository.ledger.blocks() == []
    assert accepted.accept() is accepted
