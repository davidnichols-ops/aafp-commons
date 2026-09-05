"""Versioned, content-addressed constitution manifests.

Constitutions describe mechanical packet-admission constraints. They do not
identify an agent, authorize a signer, establish provenance, or assign
reputation.

Optional ``guidance``, ``source``, ``runtime_compatibility``, and
``provider_constraints`` metadata may be attached to a manifest for
agent-readable context. These fields are advisory only — they do not
participate in admission decisions, grant authority, establish provenance,
or contribute reputation.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

from aafp_commons.canonical import digest
from aafp_commons.models import (
    ConstitutionRef,
    KnowledgePacket,
    PacketKind,
    Visibility,
)

_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_VERSION = re.compile(r"^[0-9][0-9A-Za-z._+-]{0,63}$")
_NAMESPACE_PREFIX = re.compile(
    r"^(commons|org|agent)(?:/[a-z0-9][a-z0-9._/-]{0,126})?$"
)
_PACKET_KINDS: frozenset[str] = frozenset(
    {"observation", "hypothesis", "finding", "workflow", "benchmark"}
)
_VISIBILITIES: frozenset[str] = frozenset({"public", "organization", "private"})
CONSTITUTION_SCHEMA = "aafp.commons/constitution-manifest@1"


class ConstitutionError(ValueError):
    """Base error for invalid or unresolved constitution packages."""


class ConstitutionNotFoundError(ConstitutionError):
    """Raised when an exact constitution version is unavailable."""


class ConstitutionIntegrityError(ConstitutionError):
    """Raised when stored constitution content does not match its reference."""


@dataclass(frozen=True)
class ConstitutionGuidance:
    """Optional agent-readable behavioral guidance attached to a constitution.

    Advisory text only. Does not grant authority, establish identity, assign
    reputation, or change admission mechanics. Agents may read it for context
    but must not treat it as an override of provider/system constraints, the
    manifest's admission rules, or the repository's policy gates.
    """

    summary: str = ""
    principles: tuple[str, ...] = ()
    text: str = ""

    def __post_init__(self) -> None:
        if self.summary and not self.summary.strip():
            raise ConstitutionError("guidance summary must not be blank")
        if any(not item.strip() for item in self.principles):
            raise ConstitutionError("guidance principles must not be blank")
        if len(set(self.principles)) != len(self.principles):
            raise ConstitutionError("guidance principles must be unique")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ConstitutionGuidance:
        data = dict(value)
        if "principles" in data:
            if not isinstance(data["principles"], (list, tuple)):
                raise ConstitutionError("guidance principles must be an array")
            data["principles"] = tuple(data["principles"])
        return cls(**data)


@dataclass(frozen=True)
class ConstitutionSource:
    """Optional source and license metadata for a constitution package.

    Advisory provenance hint only. Does not establish cryptographic
    provenance, authority, or reputation. The ``license`` field is a
    free-form SPDX-ish identifier (e.g., ``CC0-1.0``, ``Apache-2.0``).
    """

    title: str = ""
    url: str = ""
    license: str = ""
    attribution: str = ""

    def __post_init__(self) -> None:
        if self.title and not self.title.strip():
            raise ConstitutionError("source title must not be blank")
        if self.url and not self.url.strip():
            raise ConstitutionError("source url must not be blank")
        if self.license and not self.license.strip():
            raise ConstitutionError("source license must not be blank")
        if self.attribution and not self.attribution.strip():
            raise ConstitutionError("source attribution must not be blank")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ConstitutionSource:
        return cls(**dict(value))


@dataclass(frozen=True)
class RuntimeCompatibility:
    """Optional runtime/provider compatibility information for a constitution.

    Records which agent runtimes (e.g. ``claude``, ``codex``, ``cursor``) a
    constitution is known to work with, and which it is known *not* to work
    with.  This is advisory metadata for discovery; it does not restrict
    admission.  A runtime not listed in either set is simply untested.
    """

    compatible: tuple[str, ...] = ()
    incompatible: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        for value in self.compatible:
            if not _IDENTIFIER.fullmatch(value):
                raise ConstitutionError("compatible runtime identifier is invalid")
        if len(set(self.compatible)) != len(self.compatible):
            raise ConstitutionError("compatible runtimes must be unique")
        for value in self.incompatible:
            if not _IDENTIFIER.fullmatch(value):
                raise ConstitutionError("incompatible runtime identifier is invalid")
        if len(set(self.incompatible)) != len(self.incompatible):
            raise ConstitutionError("incompatible runtimes must be unique")
        overlap = set(self.compatible) & set(self.incompatible)
        if overlap:
            raise ConstitutionError(
                f"runtime cannot be both compatible and incompatible: {sorted(overlap)}"
            )

    @property
    def is_restricted(self) -> bool:
        """True if the constitution explicitly lists any compatible runtime."""
        return bool(self.compatible)

    def is_compatible(self, runtime: str) -> bool | None:
        """Return True/False if known, None if untested."""
        if runtime in self.compatible:
            return True
        if runtime in self.incompatible:
            return False
        return None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> RuntimeCompatibility:
        data = dict(value)
        for name in ("compatible", "incompatible"):
            if name in data:
                if not isinstance(data[name], (list, tuple)):
                    raise ConstitutionError(f"runtime {name} must be an array")
                data[name] = tuple(data[name])
        return cls(**data)


@dataclass(frozen=True)
class ProviderConstraint:
    """A constraint from a specific provider with explicit precedence.

    When multiple providers' constraints apply to the same constitution
    (e.g. Anthropic's safety guidelines and an operator's usage policy),
    ``precedence`` determines ordering.  Higher precedence wins conflicts.
    This is advisory metadata for agent reasoning, not a mechanical gate.
    """

    provider: str
    constraint: str
    precedence: int = 0
    source_url: str = ""

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ConstitutionError("provider constraint provider is required")
        if not _IDENTIFIER.fullmatch(self.provider):
            raise ConstitutionError("provider constraint provider must be a safe identifier")
        if not self.constraint.strip():
            raise ConstitutionError("provider constraint text is required")
        if self.source_url and not self.source_url.strip():
            raise ConstitutionError("provider constraint source_url must not be blank")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ProviderConstraint:
        return cls(**dict(value))


def constraints_by_precedence(
    constraints: tuple[ProviderConstraint, ...],
) -> list[ProviderConstraint]:
    """Return constraints sorted by descending precedence, then provider name."""
    return sorted(constraints, key=lambda c: (-c.precedence, c.provider))


def merge_constraints(
    *groups: tuple[ProviderConstraint, ...],
) -> tuple[ProviderConstraint, ...]:
    """Merge multiple constraint groups, preserving all entries.

    Duplicate (provider, constraint) pairs are collapsed to the highest
    precedence instance.  The result is ordered by descending precedence.
    """
    seen: dict[tuple[str, str], ProviderConstraint] = {}
    for group in groups:
        for constraint in group:
            key = (constraint.provider, constraint.constraint)
            existing = seen.get(key)
            if existing is None or constraint.precedence > existing.precedence:
                seen[key] = constraint
    return tuple(constraints_by_precedence(tuple(seen.values())))


def version_key(version: str) -> tuple[tuple[int, int | str], ...]:
    """Natural ordering for the safe semver-like versions used by manifests."""

    if not _VERSION.fullmatch(version):
        raise ConstitutionError("constitution version must be a safe exact version")
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.lower())
        for part in re.findall(r"[0-9]+|[A-Za-z]+", version)
    )


@dataclass(frozen=True)
class ConstitutionManifest:
    """Immutable declarative admission rules for one constitution version."""

    constitution_id: str
    version: str
    namespace_prefixes: tuple[str, ...]
    allowed_kinds: tuple[PacketKind, ...] = (
        "observation",
        "hypothesis",
        "finding",
        "workflow",
        "benchmark",
    )
    allowed_visibilities: tuple[Visibility, ...] = ("public",)
    allowed_licenses: tuple[str, ...] = ("commons-v1",)
    minimum_evidence: int = 1
    required_evidence_kinds: tuple[str, ...] = ()
    require_evidence_digests: bool = False
    supersedes: ConstitutionRef | None = None
    description: str = ""
    guidance: ConstitutionGuidance | None = None
    source: ConstitutionSource | None = None
    runtime_compatibility: RuntimeCompatibility | None = None
    provider_constraints: tuple[ProviderConstraint, ...] = field(default_factory=tuple)
    provider_constraint_policy: Literal["preserve"] = "preserve"
    schema: str = CONSTITUTION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != CONSTITUTION_SCHEMA:
            raise ConstitutionError(f"unsupported constitution schema: {self.schema}")
        if self.provider_constraint_policy != "preserve":
            raise ConstitutionError("optional constitutions must preserve provider constraints")
        if not _IDENTIFIER.fullmatch(self.constitution_id):
            raise ConstitutionError("constitution id must be a lowercase safe identifier")
        if not _VERSION.fullmatch(self.version):
            raise ConstitutionError("constitution version must be a safe exact version")
        if not self.namespace_prefixes:
            raise ConstitutionError("at least one namespace prefix is required")
        if any(not _NAMESPACE_PREFIX.fullmatch(value) for value in self.namespace_prefixes):
            raise ConstitutionError("constitution namespace prefixes are invalid")
        if len(set(self.namespace_prefixes)) != len(self.namespace_prefixes):
            raise ConstitutionError("constitution namespace prefixes must be unique")
        if not self.allowed_kinds or any(
            value not in _PACKET_KINDS for value in self.allowed_kinds
        ):
            raise ConstitutionError("constitution allowed packet kinds are invalid")
        if len(set(self.allowed_kinds)) != len(self.allowed_kinds):
            raise ConstitutionError("constitution allowed packet kinds must be unique")
        if not self.allowed_visibilities or any(
            value not in _VISIBILITIES for value in self.allowed_visibilities
        ):
            raise ConstitutionError("constitution allowed visibilities are invalid")
        if len(set(self.allowed_visibilities)) != len(self.allowed_visibilities):
            raise ConstitutionError("constitution allowed visibilities must be unique")
        if not self.allowed_licenses or any(not value.strip() for value in self.allowed_licenses):
            raise ConstitutionError("constitution allowed licenses are invalid")
        if len(set(self.allowed_licenses)) != len(self.allowed_licenses):
            raise ConstitutionError("constitution allowed licenses must be unique")
        if self.minimum_evidence < 1:
            raise ConstitutionError("constitution minimum evidence must be at least one")
        if any(not value.strip() for value in self.required_evidence_kinds):
            raise ConstitutionError("constitution required evidence kinds are invalid")
        if len(set(self.required_evidence_kinds)) != len(self.required_evidence_kinds):
            raise ConstitutionError("constitution required evidence kinds must be unique")
        if self.supersedes is not None:
            if self.supersedes.constitution_id != self.constitution_id:
                raise ConstitutionError(
                    "a constitution may supersede only the same constitution id"
                )
            if self.supersedes.version == self.version:
                raise ConstitutionError("a constitution cannot supersede its own version")
            if self.supersedes.digest is None:
                raise ConstitutionError("a superseded constitution reference must pin a digest")
        if self.provider_constraints:
            for constraint in self.provider_constraints:
                if not isinstance(constraint, ProviderConstraint):
                    raise ConstitutionError(
                        "provider constraints must be ProviderConstraint instances"
                    )
            entries = [
                (constraint.provider, constraint.constraint)
                for constraint in self.provider_constraints
            ]
            if len(set(entries)) != len(entries):
                raise ConstitutionError(
                    "provider constraint entries must be unique"
                )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        """Serialize the manifest as canonical, portable JSON."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=2) + "\n"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ConstitutionManifest:
        data = dict(value)
        for name in (
            "namespace_prefixes",
            "allowed_kinds",
            "allowed_visibilities",
            "allowed_licenses",
            "required_evidence_kinds",
        ):
            if name in data:
                if not isinstance(data[name], (list, tuple)):
                    raise ConstitutionError(f"constitution {name} must be an array")
                data[name] = tuple(data[name])
        if data.get("supersedes") is not None:
            data["supersedes"] = ConstitutionRef(**data["supersedes"])
        if data.get("guidance") is not None:
            data["guidance"] = ConstitutionGuidance.from_dict(data["guidance"])
        if data.get("source") is not None:
            data["source"] = ConstitutionSource.from_dict(data["source"])
        if data.get("runtime_compatibility") is not None:
            data["runtime_compatibility"] = RuntimeCompatibility.from_dict(
                data["runtime_compatibility"]
            )
        if data.get("provider_constraints") is not None:
            if not isinstance(data["provider_constraints"], (list, tuple)):
                raise ConstitutionError("provider constraints must be an array")
            data["provider_constraints"] = tuple(
                ProviderConstraint.from_dict(item) for item in data["provider_constraints"]
            )
        return cls(**data)

    @classmethod
    def from_json(cls, value: str) -> ConstitutionManifest:
        """Parse and validate one portable manifest JSON document."""
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as error:
            raise ConstitutionError(f"invalid constitution manifest JSON: {error}") from error
        if not isinstance(decoded, dict):
            raise ConstitutionError("constitution manifest JSON must be an object")
        return cls.from_dict(decoded)

    @property
    def manifest_digest(self) -> str:
        return digest(self.to_dict())

    @property
    def ref(self) -> ConstitutionRef:
        return ConstitutionRef(self.constitution_id, self.version, self.manifest_digest)

    def validate_packet(self, packet: KnowledgePacket) -> tuple[str, ...]:
        """Return only constitution-rule violations, without authority inference."""

        reasons: list[str] = []
        if not self.applies_to_namespace(packet.namespace):
            reasons.append("packet namespace is outside the constitution scope")
        if packet.kind not in self.allowed_kinds:
            reasons.append("packet kind is not allowed by the constitution")
        if packet.visibility not in self.allowed_visibilities:
            reasons.append("packet visibility is not allowed by the constitution")
        if packet.license not in self.allowed_licenses:
            reasons.append("packet license is not allowed by the constitution")
        if len(packet.evidence) < self.minimum_evidence:
            reasons.append(
                f"constitution requires at least {self.minimum_evidence} evidence references"
            )
        evidence_kinds = {item.kind for item in packet.evidence}
        missing_kinds = sorted(set(self.required_evidence_kinds) - evidence_kinds)
        if missing_kinds:
            reasons.append(
                "constitution requires evidence kinds: " + ", ".join(missing_kinds)
            )
        if self.require_evidence_digests and any(item.digest is None for item in packet.evidence):
            reasons.append("constitution requires content-addressed evidence")
        return tuple(reasons)

    def applies_to_namespace(self, namespace: str) -> bool:
        return any(_namespace_matches(namespace, prefix) for prefix in self.namespace_prefixes)


class ConstitutionResolver(Protocol):
    def resolve(self, reference: ConstitutionRef) -> ConstitutionManifest: ...


# Module-level alias to avoid mypy resolving ``list`` as the method name on
# classes that define a ``list`` method (FileConstitutionResolver.list).
_ManifestList = list[ConstitutionManifest]


class FileConstitutionResolver:
    """Resolve immutable manifests from ``<root>/<id>/<version>.json``."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def manifest_path(self, constitution_id: str, version: str) -> Path:
        if not _IDENTIFIER.fullmatch(constitution_id) or not _VERSION.fullmatch(version):
            raise ConstitutionError("constitution reference contains an unsafe id or version")
        return self.root / constitution_id / f"{version}.json"

    def install(self, manifest: ConstitutionManifest) -> ConstitutionRef:
        """Install once; changing an existing version is an attempted mutation."""

        path = self.manifest_path(manifest.constitution_id, manifest.version)
        encoded = manifest.to_json()
        if path.exists():
            existing = self._read(path)
            if existing != manifest:
                raise ConstitutionIntegrityError(
                    "constitution version already exists with different content"
                )
            return existing.ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded, encoding="utf-8")
        return manifest.ref

    def install_json(self, value: str) -> ConstitutionRef:
        """Validate and install one portable manifest JSON document."""
        return self.install(ConstitutionManifest.from_json(value))

    def resolve(self, reference: ConstitutionRef) -> ConstitutionManifest:
        path = self.manifest_path(reference.constitution_id, reference.version)
        if not path.exists():
            raise ConstitutionNotFoundError(
                f"constitution {reference.constitution_id}@{reference.version} is not installed"
            )
        manifest = self._read(path)
        if (
            manifest.constitution_id != reference.constitution_id
            or manifest.version != reference.version
        ):
            raise ConstitutionIntegrityError("constitution file identity does not match its path")
        if reference.digest is not None and manifest.manifest_digest != reference.digest:
            raise ConstitutionIntegrityError(
                "constitution manifest digest does not match reference"
            )
        return manifest

    def list(self) -> _ManifestList:
        """List all installed constitution manifests, sorted by id then version."""
        if not self.root.exists():
            return []
        manifests: list[ConstitutionManifest] = []
        for constitution_dir in sorted(self.root.iterdir()):
            if not constitution_dir.is_dir():
                continue
            for manifest_file in sorted(constitution_dir.glob("*.json")):
                manifests.append(
                    self._read_expected(
                        manifest_file,
                        constitution_dir.name,
                        manifest_file.stem,
                    )
                )
        return manifests

    def find(self, constitution_id: str) -> _ManifestList:
        """List all installed versions of a constitution by id."""
        if not _IDENTIFIER.fullmatch(constitution_id):
            raise ConstitutionError("constitution id must be a lowercase safe identifier")
        constitution_dir = self.root / constitution_id
        if not constitution_dir.exists():
            return []
        return [
            self._read_expected(path, constitution_id, path.stem)
            for path in sorted(constitution_dir.glob("*.json"))
        ]

    @classmethod
    def _read_expected(
        cls,
        path: Path,
        constitution_id: str,
        version: str,
    ) -> ConstitutionManifest:
        if not _IDENTIFIER.fullmatch(constitution_id) or not _VERSION.fullmatch(version):
            raise ConstitutionIntegrityError("constitution manifest path is unsafe")
        manifest = cls._read(path)
        if manifest.constitution_id != constitution_id or manifest.version != version:
            raise ConstitutionIntegrityError("constitution file identity does not match its path")
        return manifest

    @staticmethod
    def _read(path: Path) -> ConstitutionManifest:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ConstitutionIntegrityError("constitution manifest must be a JSON object")
            return ConstitutionManifest.from_dict(value)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ConstitutionError) as error:
            if isinstance(error, ConstitutionIntegrityError):
                raise
            raise ConstitutionIntegrityError(f"invalid constitution manifest: {error}") from error


def _namespace_matches(namespace: str, prefix: str) -> bool:
    normalized = prefix.rstrip("/")
    return namespace == normalized or namespace.startswith(normalized + "/")
