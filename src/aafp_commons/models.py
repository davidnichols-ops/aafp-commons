"""Immutable protocol objects for the shared research graph."""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from aafp_commons.canonical import digest
from aafp_commons.identity import validate_agent_id

PacketKind = Literal["observation", "hypothesis", "finding", "workflow", "benchmark"]
Visibility = Literal["public", "organization", "private"]

_NAMESPACE = re.compile(r"^(commons|org|agent)/[a-z0-9][a-z0-9._/-]{1,126}$")


@dataclass(frozen=True)
class EvidenceRef:
    kind: str
    uri: str
    observed_at: int = field(default_factory=lambda: int(time.time()))
    digest: str | None = None
    summary: str | None = None

    def __post_init__(self) -> None:
        if not self.kind.strip() or not self.uri.strip():
            raise ValueError("evidence kind and uri are required")
        if self.digest is not None and not self.digest.startswith("sha256:"):
            raise ValueError("evidence digest must be a sha256 content address")


@dataclass(frozen=True)
class ConstitutionRef:
    constitution_id: str
    version: str
    digest: str | None = None

    def __post_init__(self) -> None:
        if not self.constitution_id.strip() or not self.version.strip():
            raise ValueError("constitution id and version are required")
        if self.digest is not None and not self.digest.startswith("sha256:"):
            raise ValueError("constitution digest must be a sha256 content address")


@dataclass(frozen=True)
class MethodRef:
    name: str
    version: str
    uri: str | None = None
    digest: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.version.strip():
            raise ValueError("method name and version are required")
        if self.digest is not None and not self.digest.startswith("sha256:"):
            raise ValueError("method digest must be a sha256 content address")


@dataclass(frozen=True)
class KnowledgePacket:
    kind: PacketKind
    namespace: str
    claim: str
    scope: dict[str, Any]
    evidence: tuple[EvidenceRef, ...]
    confidence: float
    author_agent_id: str
    constitution: ConstitutionRef
    method: MethodRef
    created_at: int = field(default_factory=lambda: int(time.time()))
    expires_at: int | None = None
    dependencies: tuple[str, ...] = ()
    contradicts: tuple[str, ...] = ()
    supersedes: tuple[str, ...] = ()
    visibility: Visibility = "public"
    license: str = "commons-v1"
    schema: str = "aafp.commons/knowledge-packet@1"

    def __post_init__(self) -> None:
        if not _NAMESPACE.fullmatch(self.namespace):
            raise ValueError("namespace must begin with commons/, org/, or agent/")
        if len(self.claim.strip()) < 12:
            raise ValueError("claim must be specific enough to evaluate")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not self.evidence:
            raise ValueError("at least one evidence reference is required")
        if self.expires_at is not None and self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
        validate_agent_id(self.author_agent_id)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> KnowledgePacket:
        data = dict(value)
        data["evidence"] = tuple(EvidenceRef(**item) for item in data["evidence"])
        data["constitution"] = ConstitutionRef(**data["constitution"])
        data["method"] = MethodRef(**data["method"])
        for name in ("dependencies", "contradicts", "supersedes"):
            data[name] = tuple(data.get(name, ()))
        return cls(**data)

    @property
    def packet_id(self) -> str:
        return digest(self.to_dict())

