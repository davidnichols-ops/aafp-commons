"""Minimal local agent-first constitution join walkthrough."""

from pathlib import Path

from aafp_commons import (
    AgentJoinSession,
    CommonsRepository,
    RuntimeHandshake,
    default_registry,
    derive_agent_id,
)


def main() -> None:
    root = Path("commons-data")
    repository = CommonsRepository(root)
    repository.install_constitution(default_registry().get("grok-truth-seeking").manifest)
    session = AgentJoinSession.begin(
        repository,
        RuntimeHandshake(
            runtime="grok",
            runtime_version="grok-3",
            identity_convention="runtime-native",
            identity_hint="local example session",
        ),
        agent_id=derive_agent_id(b"example-agent"),
        namespace="commons/research",
        packet_kind="finding",
        constitution="grok-truth-seeking@1.0.0",
    )
    accepted = session.accept()
    print(accepted.working_context()["guidance"])


if __name__ == "__main__":
    main()
