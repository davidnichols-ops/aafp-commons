"""Machine-readable requests to adopt optional constitution guidance.

An adoption request records an agent's preference to work under one exact,
digest-pinned constitution.  It is intentionally not an identity proof,
signature, capability, authorization, provenance claim, or reputation signal.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from aafp_commons.canonical import digest
from aafp_commons.constitutions import ConstitutionResolver
from aafp_commons.identity import validate_agent_id
from aafp_commons.models import ConstitutionRef, PacketKind

ADOPTION_REQUEST_SCHEMA = "aafp.commons/constitution-adoption-request@1"
ADOPTION_DECISION_SCHEMA = "aafp.commons/constitution-adoption-decision@1"
ADOPTION_BOUNDARY = (
    "This request expresses an optional guidance preference only. It is unsigned and "
    "does not prove AAFP identity, grant authority, establish provenance, assign "
    "reputation, or override provider, system, authorization, or repository constraints."
)

_RUNTIME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_NAMESPACE = re.compile(r"^(commons|org|agent)/[a-z0-9][a-z0-9._/-]{1,126}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_PACKET_KINDS = {"observation", "hypothesis", "finding", "workflow", "benchmark"}


class AdoptionRequestError(ValueError):
    """Base error for invalid or unresolved adoption requests."""


class AdoptionRequestIntegrityError(AdoptionRequestError):
    """Raised when a stored request does not match its content address."""


class AdoptionDecisionNotFoundError(AdoptionRequestError):
    """Raised when no local runtime decision exists for a request."""


@dataclass(frozen=True)
class ConstitutionAdoptionRequest:
    """An agent-originated request to use one optional constitution."""

    requester_agent_id: str
    runtime: str
    namespace: str
    packet_kind: PacketKind
    constitution: ConstitutionRef
    purpose: str = ""
    created_at: int = field(default_factory=lambda: int(time.time()))
    provider_constraint_policy: Literal["preserve"] = "preserve"
    status: Literal["awaiting-runtime-acceptance"] = "awaiting-runtime-acceptance"
    schema: str = ADOPTION_REQUEST_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != ADOPTION_REQUEST_SCHEMA:
            raise ValueError(f"unsupported adoption request schema: {self.schema}")
        if not isinstance(self.requester_agent_id, str):
            raise ValueError("requester_agent_id must be a string")
        validate_agent_id(self.requester_agent_id)
        if not isinstance(self.runtime, str) or not _RUNTIME.fullmatch(self.runtime):
            raise ValueError("runtime must be a lowercase safe identifier")
        if not isinstance(self.namespace, str) or not _NAMESPACE.fullmatch(self.namespace):
            raise ValueError("namespace must begin with commons/, org/, or agent/")
        if self.packet_kind not in _PACKET_KINDS:
            raise ValueError("packet_kind is not supported")
        if not isinstance(self.constitution, ConstitutionRef):
            raise ValueError("constitution must be a ConstitutionRef")
        if self.constitution.digest is None or not _DIGEST.fullmatch(
            self.constitution.digest
        ):
            raise ValueError("adoption requests must pin an exact sha256 constitution digest")
        if self.provider_constraint_policy != "preserve":
            raise ValueError("optional constitutions must preserve provider constraints")
        if self.status != "awaiting-runtime-acceptance":
            raise ValueError("new adoption requests must await runtime acceptance")
        if not isinstance(self.created_at, int) or isinstance(self.created_at, bool):
            raise ValueError("created_at must be an integer timestamp")
        if self.created_at < 0:
            raise ValueError("created_at cannot be negative")
        if not isinstance(self.purpose, str):
            raise ValueError("purpose must be a string")
        if self.purpose and not self.purpose.strip():
            raise ValueError("purpose cannot be whitespace only")
        if len(self.purpose) > 500:
            raise ValueError("purpose cannot exceed 500 characters")

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical request body covered by ``request_id``."""
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ConstitutionAdoptionRequest:
        """Parse a canonical request body."""
        data = dict(value)
        try:
            constitution = data.get("constitution")
            if not isinstance(constitution, dict):
                raise ValueError("adoption request constitution must be an object")
            data["constitution"] = ConstitutionRef(**constitution)
            return cls(**data)
        except (TypeError, ValueError) as error:
            raise AdoptionRequestError(f"invalid adoption request: {error}") from error

    @property
    def request_id(self) -> str:
        """Content address for the exact request body."""
        return digest(self.to_dict())

    @property
    def question(self) -> str:
        """Short prompt a runtime can present or resolve programmatically."""
        return (
            f"May agent {self.requester_agent_id} adopt "
            f"{self.constitution.constitution_id}@{self.constitution.version} as optional "
            f"guidance for {self.packet_kind} work in {self.namespace}?"
        )


class FileAdoptionRequestStore:
    """Immutable content-addressed storage for agent adoption requests."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def request_path(self, request_id: str) -> Path:
        if not _DIGEST.fullmatch(request_id):
            raise AdoptionRequestError("request id must be a sha256 content address")
        return self.root / f"{request_id.removeprefix('sha256:')}.json"

    def record(
        self,
        request: ConstitutionAdoptionRequest,
        resolver: ConstitutionResolver,
    ) -> str:
        """Resolve the exact manifest and store the request idempotently."""
        manifest = resolver.resolve(request.constitution)
        if not manifest.applies_to_namespace(request.namespace):
            raise AdoptionRequestError("request namespace is outside the constitution scope")
        if request.packet_kind not in manifest.allowed_kinds:
            raise AdoptionRequestError("request packet kind is not allowed by the constitution")
        compatibility = manifest.runtime_compatibility
        if compatibility is None or compatibility.is_compatible(request.runtime) is not True:
            raise AdoptionRequestError("request runtime is not explicitly compatible")
        if manifest.guidance is None:
            raise AdoptionRequestError("requested constitution has no agent guidance")

        request_id = request.request_id
        path = self.request_path(request_id)
        encoded = json.dumps(request.to_dict(), sort_keys=True, indent=2) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(encoded)
        except FileExistsError:
            if self.get(request_id) != request:
                raise AdoptionRequestIntegrityError(
                    "adoption request content address already has different content"
                ) from None
        return request_id

    def get(self, request_id: str) -> ConstitutionAdoptionRequest:
        """Load one request and verify its filename content address."""
        path = self.request_path(request_id)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise AdoptionRequestIntegrityError("adoption request must be a JSON object")
            request = ConstitutionAdoptionRequest.from_dict(value)
        except (OSError, json.JSONDecodeError, AdoptionRequestError) as error:
            if isinstance(error, AdoptionRequestIntegrityError):
                raise
            raise AdoptionRequestIntegrityError(f"invalid adoption request: {error}") from error
        if request.request_id != request_id:
            raise AdoptionRequestIntegrityError(
                "adoption request filename does not match its content address"
            )
        return request

    def list(self) -> list[ConstitutionAdoptionRequest]:
        """List stored requests after validating every content address."""
        if not self.root.exists():
            return []
        return [
            self.get(f"sha256:{path.stem}")
            for path in sorted(self.root.glob("*.json"))
        ]


@dataclass(frozen=True)
class ConstitutionAdoptionDecision:
    """A local runtime response to one exact adoption request.

    A decision controls only whether the local runtime exposes the requested
    guidance as working context.  It is unsigned and grants no authority.
    """

    request_id: str
    constitution: ConstitutionRef
    runtime: str
    accepted: bool
    reason: str = ""
    decided_at: int = field(default_factory=lambda: int(time.time()))
    provider_constraint_policy: Literal["preserve"] = "preserve"
    schema: str = ADOPTION_DECISION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != ADOPTION_DECISION_SCHEMA:
            raise ValueError(f"unsupported adoption decision schema: {self.schema}")
        if not isinstance(self.request_id, str) or not _DIGEST.fullmatch(self.request_id):
            raise ValueError("request_id must be a sha256 content address")
        if not isinstance(self.constitution, ConstitutionRef):
            raise ValueError("constitution must be a ConstitutionRef")
        if self.constitution.digest is None or not _DIGEST.fullmatch(
            self.constitution.digest
        ):
            raise ValueError("decisions must pin an exact sha256 constitution digest")
        if not isinstance(self.runtime, str) or not _RUNTIME.fullmatch(self.runtime):
            raise ValueError("runtime must be a lowercase safe identifier")
        if not isinstance(self.accepted, bool):
            raise ValueError("accepted must be a boolean")
        if not isinstance(self.reason, str):
            raise ValueError("reason must be a string")
        if not self.accepted and not self.reason.strip():
            raise ValueError("a rejected request requires a reason")
        if len(self.reason) > 500:
            raise ValueError("reason cannot exceed 500 characters")
        if not isinstance(self.decided_at, int) or isinstance(self.decided_at, bool):
            raise ValueError("decided_at must be an integer timestamp")
        if self.decided_at < 0:
            raise ValueError("decided_at cannot be negative")
        if self.provider_constraint_policy != "preserve":
            raise ValueError("adoption decisions must preserve provider constraints")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ConstitutionAdoptionDecision:
        data = dict(value)
        try:
            constitution = data.get("constitution")
            if not isinstance(constitution, dict):
                raise ValueError("adoption decision constitution must be an object")
            data["constitution"] = ConstitutionRef(**constitution)
            return cls(**data)
        except (TypeError, ValueError) as error:
            raise AdoptionRequestError(f"invalid adoption decision: {error}") from error

    @property
    def decision_id(self) -> str:
        return digest(self.to_dict())

    @property
    def status(self) -> Literal["accepted", "rejected"]:
        return "accepted" if self.accepted else "rejected"


class FileAdoptionDecisionStore:
    """One immutable local runtime decision per adoption request."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def request_dir(self, request_id: str) -> Path:
        if not _DIGEST.fullmatch(request_id):
            raise AdoptionRequestError("request_id must be a sha256 content address")
        return self.root / request_id.removeprefix("sha256:")

    def decision_path(self, request_id: str, decision_id: str) -> Path:
        if not _DIGEST.fullmatch(decision_id):
            raise AdoptionRequestError("decision_id must be a sha256 content address")
        return self.request_dir(request_id) / f"{decision_id.removeprefix('sha256:')}.json"

    def record(self, decision: ConstitutionAdoptionDecision) -> str:
        request_dir = self.request_dir(decision.request_id)
        request_dir.mkdir(parents=True, exist_ok=True)
        existing_paths = sorted(request_dir.glob("*.json"))
        if existing_paths:
            existing = self.get(decision.request_id)
            if existing != decision:
                raise AdoptionRequestIntegrityError(
                    "adoption request already has a different immutable decision; "
                    "submit a new request to revise it"
                )
            return existing.decision_id

        path = self.decision_path(decision.request_id, decision.decision_id)
        encoded = json.dumps(decision.to_dict(), sort_keys=True, indent=2) + "\n"
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(encoded)
        except FileExistsError:
            if self.get(decision.request_id) != decision:
                raise AdoptionRequestIntegrityError(
                    "adoption decision content address has different content"
                ) from None
        return decision.decision_id

    def get(self, request_id: str) -> ConstitutionAdoptionDecision:
        request_dir = self.request_dir(request_id)
        paths = sorted(request_dir.glob("*.json")) if request_dir.exists() else []
        if not paths:
            raise AdoptionDecisionNotFoundError(
                f"no runtime decision exists for adoption request {request_id}"
            )
        if len(paths) != 1:
            raise AdoptionRequestIntegrityError(
                "an adoption request must have exactly one immutable runtime decision"
            )
        path = paths[0]
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise AdoptionRequestIntegrityError("adoption decision must be a JSON object")
            decision = ConstitutionAdoptionDecision.from_dict(value)
        except (OSError, json.JSONDecodeError, AdoptionRequestError) as error:
            if isinstance(error, AdoptionRequestIntegrityError):
                raise
            raise AdoptionRequestIntegrityError(f"invalid adoption decision: {error}") from error
        if decision.request_id != request_id:
            raise AdoptionRequestIntegrityError(
                "adoption decision filename does not match its request id"
            )
        if path.stem != decision.decision_id.removeprefix("sha256:"):
            raise AdoptionRequestIntegrityError(
                "adoption decision filename does not match its content address"
            )
        return decision

    def list(self) -> list[ConstitutionAdoptionDecision]:
        if not self.root.exists():
            return []
        return [
            self.get(f"sha256:{path.name}")
            for path in sorted(self.root.iterdir())
            if path.is_dir()
        ]
