"""Append-only conflict projection and signed local resolutions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from ironclad.trust import Identity

from aafp_commons.constitutions import ConstitutionManifest
from aafp_commons.identity import derive_agent_id
from aafp_commons.models import EvidenceRef, KnowledgePacket, MethodRef
from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import sign_packet
from aafp_commons.verification import _results, verify_object

ResolutionDecision = Literal["prefer-a", "prefer-b", "neither", "escalate"]
RESOLUTION_NAMESPACE = "commons/review/resolution"


def _review_results(repository: CommonsRepository, claim_id: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for item in repository.query("commons/review/result"):
        scope = item.packet.scope
        if scope.get("claim_id") == claim_id:
            values.append({"digest": item.packet.packet_id, "kind": "review", **scope})
    return values


def _incompatible(values: list[dict[str, Any]]) -> bool:
    by_method: dict[str, set[str]] = {}
    for value in values:
        method = str(value.get("method_id", value.get("method", "review")))
        outcome = str(value.get("outcome", value.get("decision", "")))
        by_method.setdefault(method, set()).add(outcome)
    for outcomes in by_method.values():
        if len(outcomes) > 1:
            return True
    support = {
        value.get("outcome", value.get("decision"))
        in {"supported", "reproduced", "accept-display"}
        for value in values
    }
    return len(support) > 1


def projection(
    repository: CommonsRepository, claim_id: str, policy: dict[str, Any]
) -> dict[str, Any]:
    verification = [value for value in _results(repository.root, claim_id) if verify_object(value)]
    reviews = _review_results(repository, claim_id)
    all_values = verification + reviews
    verification_digests = [value["verification_id"] for value in verification]
    review_digests = [value["digest"] for value in reviews]
    conflict = _incompatible(all_values)
    conflict_digests = verification_digests + review_digests if conflict else []
    resolutions = [
        item for item in repository.query(RESOLUTION_NAMESPACE)
        if item.packet.scope.get("claim_id") == claim_id
    ]
    supported = any(value.get("outcome") == "supported" for value in verification)
    independent = any(
        value.get("verifier_agent_id") != repository.get(claim_id).packet.author_agent_id
        for value in verification
    )
    rely_ok = not conflict
    return {
        "verification_results": verification_digests,
        "review_results": review_digests,
        "conflict": conflict,
        "conflict_digests": conflict_digests,
        "resolution_digests": [item.packet.packet_id for item in resolutions],
        "supported": supported and not conflict,
        "independent_corroboration": independent and not conflict,
        "rely_ok": rely_ok,
    }


def resolve(
    repository: CommonsRepository,
    claim_id: str,
    identity: Identity,
    constitution: ConstitutionManifest,
    preferred_digest: str,
    rationale: str,
) -> dict[str, Any]:
    current = projection(repository, claim_id, {})
    if not current["conflict"]:
        raise ValueError("no conflict exists for claim")
    if preferred_digest not in current["conflict_digests"]:
        raise ValueError("--prefer must reference a conflicting result digest")
    decision = "prefer-a" if preferred_digest == current["conflict_digests"][0] else "prefer-b"
    subject = derive_agent_id(identity.public_bytes())
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    packet = KnowledgePacket(
        kind="finding", namespace=RESOLUTION_NAMESPACE,
        claim=f"Resolution for conflicting results on {claim_id}.",
        scope={
            "schema": "aafp.commons/review-resolution@1",
            "claim_id": claim_id,
            "conflict_digests": current["conflict_digests"],
            "decision": decision, "rationale": rationale,
            "resolver_subject": subject, "method": "local-explicit-resolution",
            "resolved_at": now,
        }, confidence=1.0, author_agent_id=subject,
        evidence=tuple(EvidenceRef(kind="result", uri=f"packet://{digest}", digest=digest)
                       for digest in current["conflict_digests"]),
        constitution=constitution.ref, method=MethodRef("commons-review", "1"),
    )
    result = repository.submit(sign_packet(packet, identity), identity)
    if not result.accepted:
        raise ValueError("resolution rejected: " + "; ".join(result.reasons))
    return {"resolution_id": packet.packet_id, "decision": decision,
            "conflict_digests": current["conflict_digests"]}
