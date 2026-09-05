"""Agent-first composition of runtime handshake and constitution adoption."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from aafp_commons.adoption import ADOPTION_BOUNDARY, ConstitutionAdoptionRequest
from aafp_commons.constitutions import ConstitutionManifest
from aafp_commons.discovery import ConstitutionCatalog
from aafp_commons.handshake import RuntimeHandshake
from aafp_commons.models import PacketKind
from aafp_commons.repository import CommonsRepository


@dataclass(frozen=True)
class AgentJoinSession:
    """Stateful local join flow; it never grants authority or writes the ledger."""

    repository: CommonsRepository
    request: ConstitutionAdoptionRequest
    manifest: ConstitutionManifest
    handshake_id: str
    state: Literal["awaiting-runtime-acceptance", "accepted", "rejected"] = (
        "awaiting-runtime-acceptance"
    )

    @classmethod
    def begin(
        cls,
        repository: CommonsRepository,
        handshake: RuntimeHandshake,
        *,
        agent_id: str,
        namespace: str,
        packet_kind: PacketKind,
        purpose: str = "",
        constitution: str | None = None,
        created_at: int | None = None,
    ) -> AgentJoinSession:
        """Record a handshake and create one exact adoption request."""
        handshake_id = repository.record_runtime_handshake(handshake)
        catalog = ConstitutionCatalog(repository.constitutions)  # type: ignore[arg-type]
        if constitution is None:
            preferred = catalog.select_for_handshake(
                handshake, namespace, packet_kind, require_guidance=True
            )
            if preferred is not None:
                constitution = f"{preferred.constitution_id}@{preferred.version}"
        result = catalog.request_adoption(
            requester_agent_id=agent_id,
            runtime=handshake.runtime,
            namespace=namespace,
            packet_kind=packet_kind,
            purpose=purpose,
            created_at=created_at,
            constitution=constitution,
        )
        if result is None:
            raise ValueError("no compatible installed constitution with guidance matched")
        request, manifest = result
        repository.record_adoption_request(request)
        return cls(repository, request, manifest, handshake_id)

    def accept(self, *, reason: str = "", decided_at: int | None = None) -> AgentJoinSession:
        if self.state == "accepted":
            return self
        if self.state == "rejected":
            raise ValueError("join session was already rejected")
        decision = self.repository.respond_to_adoption_request(
            self.request.request_id, accepted=True, reason=reason, decided_at=decided_at
        )
        return AgentJoinSession(
            self.repository, self.request, self.manifest, self.handshake_id, decision.status
        )

    def reject(self, reason: str, *, decided_at: int | None = None) -> AgentJoinSession:
        if self.state == "rejected":
            return self
        if self.state == "accepted":
            raise ValueError("join session was already accepted")
        decision = self.repository.respond_to_adoption_request(
            self.request.request_id, accepted=False, reason=reason, decided_at=decided_at
        )
        return AgentJoinSession(
            self.repository, self.request, self.manifest, self.handshake_id, decision.status
        )

    def working_context(self) -> dict[str, object]:
        """Return active guidance only after acceptance, otherwise fail closed."""
        if self.state != "accepted":
            raise ValueError("join session has no active working context")
        decision = self.repository.adoption_decisions.get(self.request.request_id)
        guidance = self.manifest.guidance
        return {
            "schema": "aafp.commons/constitution-working-context@1",
            "active": True,
            "request_id": self.request.request_id,
            "decision_id": decision.decision_id,
            "handshake_id": self.handshake_id,
            "runtime": self.request.runtime,
            "namespace": self.request.namespace,
            "packet_kind": self.request.packet_kind,
            "constitution": self.request.constitution.__dict__,
            "guidance": None if guidance is None else {
                "summary": guidance.summary,
                "principles": list(guidance.principles),
                "text": guidance.text,
            },
            "provider_constraints": [c.to_dict() for c in self.manifest.provider_constraints],
            "provider_constraint_policy": self.manifest.provider_constraint_policy,
            "boundary": ADOPTION_BOUNDARY,
        }
