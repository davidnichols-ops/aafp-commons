"""Agent-first discovery and selection of installed constitutions.

Provides a lightweight catalog over a :class:`FileConstitutionResolver` that
lets agent runtimes discover, filter, and select constitutions by runtime
compatibility, namespace, packet kind, or guidance presence — without
loading every manifest into memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from aafp_commons.adoption import ConstitutionAdoptionRequest
from aafp_commons.constitutions import (
    ConstitutionManifest,
    FileConstitutionResolver,
    version_key,
)
from aafp_commons.handshake import RuntimeHandshake

# Module-level aliases to avoid mypy resolving ``list`` as the method name on
# classes that define a ``list`` method (ConstitutionCatalog.list).
_SummaryList = list["ConstitutionSummary"]
_ManifestList = list[ConstitutionManifest]


@dataclass(frozen=True)
class ConstitutionSummary:
    """Lightweight summary for discovery without loading the full manifest."""

    constitution_id: str
    version: str
    digest: str
    description: str
    compatible_runtimes: tuple[str, ...]
    incompatible_runtimes: tuple[str, ...]
    has_guidance: bool
    source_license: str
    source_title: str
    provider_count: int

    @classmethod
    def from_manifest(cls, manifest: ConstitutionManifest) -> ConstitutionSummary:
        rc = manifest.runtime_compatibility
        source = manifest.source
        return cls(
            constitution_id=manifest.constitution_id,
            version=manifest.version,
            digest=manifest.manifest_digest,
            description=manifest.description,
            compatible_runtimes=rc.compatible if rc else (),
            incompatible_runtimes=rc.incompatible if rc else (),
            has_guidance=manifest.guidance is not None,
            source_license=source.license if source else "",
            source_title=source.title if source else "",
            provider_count=len(manifest.provider_constraints),
        )


class ConstitutionCatalog:
    """Agent-first discovery and selection over installed constitutions.

    Wraps a :class:`FileConstitutionResolver` (or any resolver that supports
    ``list()``) and provides filtering and selection methods oriented toward
    agent runtimes that need to pick a constitution before proposing packets.
    """

    def __init__(self, resolver: FileConstitutionResolver | _ListableResolver) -> None:
        self._resolver = resolver

    def list(self) -> _SummaryList:
        """List all installed constitutions as lightweight summaries."""
        return [ConstitutionSummary.from_manifest(m) for m in self._resolver.list()]

    def find(self, constitution_id: str) -> _SummaryList:
        """Find all versions of a constitution by ID."""
        if not isinstance(self._resolver, FileConstitutionResolver):
            return [
                ConstitutionSummary.from_manifest(m)
                for m in self._resolver.list()
                if m.constitution_id == constitution_id
            ]
        return [
            ConstitutionSummary.from_manifest(m)
            for m in self._resolver.find(constitution_id)
        ]

    def compatible(self, runtime: str) -> _SummaryList:
        """List constitutions explicitly compatible with a runtime."""
        results: _SummaryList = []
        for summary in self.list():
            if runtime in summary.compatible_runtimes:
                results.append(summary)
        return results

    def excluded(self, runtime: str) -> _SummaryList:
        """List constitutions explicitly incompatible with a runtime."""
        results: _SummaryList = []
        for summary in self.list():
            if runtime in summary.incompatible_runtimes:
                results.append(summary)
        return results

    def with_guidance(self) -> _SummaryList:
        """List constitutions that carry agent-readable guidance."""
        return [s for s in self.list() if s.has_guidance]

    def select(
        self,
        runtime: str | None = None,
        namespace: str | None = None,
        packet_kind: str | None = None,
        require_guidance: bool = False,
    ) -> ConstitutionManifest | None:
        """Select the best constitution for the given constraints.

        Filters installed constitutions by runtime compatibility (if
        specified), namespace scope (if specified), packet kind (if
        specified), and guidance presence (if required).  Returns the
        highest-version match, or None if no constitution satisfies all
        constraints.
        """
        candidates: _ManifestList = []
        for manifest in self._resolver.list():
            if runtime is not None:
                rc = manifest.runtime_compatibility
                if rc is None or rc.is_compatible(runtime) is not True:
                    continue
            if namespace is not None and not manifest.applies_to_namespace(namespace):
                continue
            if packet_kind is not None and packet_kind not in manifest.allowed_kinds:
                continue
            if require_guidance and manifest.guidance is None:
                continue
            candidates.append(manifest)

        if not candidates:
            return None

        return max(candidates, key=lambda m: (version_key(m.version), m.constitution_id))

    def request_adoption(
        self,
        *,
        requester_agent_id: str,
        runtime: str,
        namespace: str,
        packet_kind: str,
        purpose: str = "",
        created_at: int | None = None,
        constitution: str | None = None,
    ) -> tuple[ConstitutionAdoptionRequest, ConstitutionManifest] | None:
        """Select guidance and form an agent-originated adoption request.

        The returned request is content-addressed but unsigned.  Callers must
        not treat it as identity proof or authorization.  Returning the exact
        manifest alongside it lets a runtime inspect the digest-covered
        guidance before accepting the preference.
        """
        if constitution is not None:
            parts = constitution.split("@")
            if len(parts) != 2 or not all(parts):
                raise ValueError("constitution must use the exact ID@VERSION form")
            matches = [
                candidate
                for candidate in self._resolver.list()
                if candidate.constitution_id == parts[0] and candidate.version == parts[1]
            ]
            if not matches:
                raise ValueError(f"constitution {constitution} is not installed")
            manifest = matches[0]
            if not manifest.applies_to_namespace(namespace):
                raise ValueError("requested constitution is outside the namespace scope")
            if packet_kind not in manifest.allowed_kinds:
                raise ValueError("requested constitution does not allow this packet kind")
            compatibility = manifest.runtime_compatibility
            if compatibility is None or compatibility.is_compatible(runtime) is not True:
                raise ValueError(
                    "requested constitution is not explicitly compatible with this runtime"
                )
            if manifest.guidance is None:
                raise ValueError("requested constitution has no agent guidance")
        else:
            selected = self.select(
                runtime=runtime,
                namespace=namespace,
                packet_kind=packet_kind,
                require_guidance=True,
            )
            if selected is None:
                return None
            manifest = selected
        if manifest is None:
            return None
        request_kwargs: dict[str, object] = {
            "requester_agent_id": requester_agent_id,
            "runtime": runtime,
            "namespace": namespace,
            "packet_kind": packet_kind,
            "constitution": manifest.ref,
            "purpose": purpose,
        }
        if created_at is not None:
            request_kwargs["created_at"] = created_at
        request = ConstitutionAdoptionRequest(**request_kwargs)  # type: ignore[arg-type]
        return request, manifest

    def select_for_handshake(
        self,
        handshake: RuntimeHandshake,
        namespace: str,
        packet_kind: str,
        require_guidance: bool = True,
    ) -> ConstitutionManifest | None:
        """Select guidance for a runtime, preferring its exact accepted refs."""
        accepted = {
            (ref.constitution_id, ref.version, ref.digest)
            for ref in handshake.accepted_constitutions
        }
        candidates: _ManifestList = []
        for manifest in self._resolver.list():
            compatibility = manifest.runtime_compatibility
            if compatibility is None or compatibility.is_compatible(handshake.runtime) is not True:
                continue
            if not manifest.applies_to_namespace(namespace):
                continue
            if packet_kind not in manifest.allowed_kinds:
                continue
            if require_guidance and manifest.guidance is None:
                continue
            candidates.append(manifest)
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda manifest: (
                (manifest.constitution_id, manifest.version, manifest.manifest_digest) in accepted,
                version_key(manifest.version),
                manifest.constitution_id,
            ),
        )


class _ListableResolver(Protocol):
    """Protocol for resolvers that support listing installed manifests."""

    def list(self) -> _ManifestList: ...
