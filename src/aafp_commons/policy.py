"""Mechanical admission gates for candidate knowledge packets."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any

from aafp_commons.constitutions import ConstitutionManifest
from aafp_commons.signing import SignedPacket
from aafp_commons.ucan import UcanError, verify_ucan

_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(api[_-]?key|secret|password|private[_-]?key)\s*[:=]\s*\S+"),
    re.compile(r"\b(?:sk|ghp|xoxb)-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


@dataclass(frozen=True)
class PolicyDecision:
    accepted: bool
    status: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class AdmissionPolicy:
    max_clock_skew_seconds: int = 300
    require_public_evidence_uri: bool = True
    require_constitution_digest: bool = True

    def evaluate(
        self,
        signed: SignedPacket,
        constitution: ConstitutionManifest | None = None,
        now: int | None = None,
        ucan: str | None = None,
    ) -> PolicyDecision:
        current = int(time.time()) if now is None else now
        reasons: list[str] = []
        packet = signed.packet
        if not signed.verify():
            reasons.append("invalid Ironclad signature or receipt")
        if self.require_constitution_digest and packet.constitution.digest is None:
            reasons.append("packet constitution must pin a manifest digest")
        if constitution is None:
            reasons.append("packet constitution could not be resolved")
        else:
            if (
                packet.constitution.constitution_id != constitution.constitution_id
                or packet.constitution.version != constitution.version
                or (
                    packet.constitution.digest is not None
                    and packet.constitution.digest != constitution.manifest_digest
                )
            ):
                reasons.append("resolved constitution does not match the packet reference")
            else:
                reasons.extend(constitution.validate_packet(packet))
        if packet.created_at > current + self.max_clock_skew_seconds:
            reasons.append("packet creation time is too far in the future")
        if packet.expires_at is not None and packet.expires_at <= current:
            reasons.append("packet is expired")
        if (
            self.require_public_evidence_uri
            and packet.visibility == "public"
            and any(not ref.uri for ref in packet.evidence)
        ):
            reasons.append("public packets require evidence URIs")
        if _contains_secret(packet.to_dict()):
            reasons.append("packet appears to contain secret material")
        require_ucan = os.environ.get("COMMONS_REQUIRE_UCAN") == "1"
        if require_ucan and ucan is None:
            reasons.append("UCAN_REQUIRED")
        elif ucan is not None:
            try:
                verify_ucan(ucan, packet, now=current)
            except UcanError as error:
                reasons.append(str(error))
        return PolicyDecision(
            accepted=not reasons,
            status="admissible" if not reasons else "rejected",
            reasons=tuple(reasons),
        )


def _contains_secret(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_secret(key) or _contains_secret(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_secret(item) for item in value)
    if isinstance(value, str):
        return any(pattern.search(value) is not None for pattern in _SECRET_PATTERNS)
    return False
