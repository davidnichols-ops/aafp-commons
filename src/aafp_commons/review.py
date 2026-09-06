"""Local review queue and signed review-result packets."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from ironclad.trust import Identity

from aafp_commons.constitutions import ConstitutionManifest
from aafp_commons.identity import derive_agent_id
from aafp_commons.models import EvidenceRef, KnowledgePacket, MethodRef
from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import sign_packet

Decision = Literal[
    "accept-display",
    "need-evidence",
    "reject-spam",
    "reject-scope",
    "reject-constitution",
    "conflict",
    "escalate",
]
DECISIONS = {
    "accept-display", "need-evidence", "reject-spam", "reject-scope",
    "reject-constitution", "conflict", "escalate",
}
REVIEW_NAMESPACE = "commons/review/result"
REVIEW_SCHEMA = "aafp.commons/review-result@1"


@dataclass(frozen=True)
class ReviewQueueItem:
    claim_id: str
    state: str
    enqueued_at: int
    reviewer_subject: str | None = None
    last_transition_at: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "state": self.state,
            "enqueued_at": self.enqueued_at,
            "reviewer_subject": self.reviewer_subject,
            "last_transition_at": self.last_transition_at or self.enqueued_at,
        }


def _review_packets(repository: CommonsRepository, claim_id: str) -> list[Any]:
    return [
        item for item in repository.query(REVIEW_NAMESPACE)
        if item.packet.scope.get("claim_id") == claim_id
    ]


def queue(
    repository: CommonsRepository,
    claim_id: str,
    reviewer_subject: str | None = None,
) -> dict[str, Any]:
    claim = repository.get(claim_id)
    existing = _review_packets(repository, claim_id)
    terminal = any(item.packet.scope.get("decision") in DECISIONS for item in existing)
    if terminal:
        return ReviewQueueItem(
            claim_id, "complete", claim.packet.created_at, reviewer_subject
        ).to_dict()
    now = int(time.time())
    return ReviewQueueItem(claim_id, "in-review", now, reviewer_subject, now).to_dict()


def _mechanical_screen(repository: CommonsRepository, claim: Any) -> list[str]:
    reasons: list[str] = []
    if claim.packet.kind != "finding":
        reasons.append("reject-scope")
    if not claim.packet.evidence:
        reasons.append("need-evidence")
    if all(
        reference.uri.startswith(("artifact://", "file://"))
        for reference in claim.packet.evidence
    ):
        reasons.append("need-evidence")
    if any(
        reference.uri.startswith(("/", "http://", "https://"))
        for reference in claim.packet.evidence
    ):
        reasons.append("private-reference")
    return sorted(set(reasons))


def decide(
    repository: CommonsRepository,
    claim_id: str,
    identity: Identity,
    constitution: ConstitutionManifest,
    decision: Decision,
    bundle_id: str | None = None,
) -> dict[str, Any]:
    if decision not in DECISIONS:
        raise ValueError("invalid review decision")
    claim = repository.get(claim_id)
    mechanical = _mechanical_screen(repository, claim)
    if mechanical and decision == "accept-display":
        raise ValueError("mechanical review screen: " + ",".join(mechanical))
    reviewer_agent_id = derive_agent_id(identity.public_bytes())
    evidence = [EvidenceRef(kind="claim", uri=f"packet://{claim_id}", digest=claim_id)]
    if bundle_id:
        evidence.append(
            EvidenceRef(
                kind="evidence-bundle", uri=f"bundle://{bundle_id}", digest=bundle_id
            )
        )
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    same_operator = reviewer_agent_id == claim.packet.author_agent_id
    review = KnowledgePacket(
        kind="finding",
        namespace=REVIEW_NAMESPACE,
        claim=f"Review decision for admitted claim {claim_id}.",
        scope={
            "schema": REVIEW_SCHEMA,
            "claim_id": claim_id,
            "decision": decision,
            "evidence_digests": [claim_id] + ([bundle_id] if bundle_id else []),
            "reviewed_under": {
                "constitution_id": constitution.constitution_id,
                "version": constitution.version,
                "digest": constitution.manifest_digest,
            },
            "reviewer_subject": reviewer_agent_id,
            "publisher_subject": claim.packet.author_agent_id,
            "same_operator": same_operator,
            "independent": not same_operator,
            "queue_state": "escalated" if decision == "escalate" else "decided",
            "enqueued_at": datetime.fromtimestamp(
                claim.packet.created_at, UTC
            ).isoformat().replace("+00:00", "Z"),
            "decided_at": now,
            "checks": [
                {"name": "mechanical-screen", "passed": not mechanical,
                 "detail": ",".join(mechanical) or "no mechanical failures"},
            ],
            "rationale": "local review decision; admission and support remain separate",
        },
        evidence=tuple(evidence), confidence=1.0,
        author_agent_id=reviewer_agent_id,
        constitution=constitution.ref,
        method=MethodRef("commons-review", "1"),
    )
    signed = sign_packet(review, identity)
    result = repository.submit(signed, identity)
    if not result.accepted:
        raise ValueError("review result rejected: " + "; ".join(result.reasons))
    return {"review_id": review.packet_id, "decision": decision, "independent": not same_operator}
