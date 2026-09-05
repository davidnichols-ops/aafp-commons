"""Agent-first discovery and selection of built-in constitution packages.

A constitution package bundles an immutable :class:`ConstitutionManifest`
with display metadata (name, description, tags) so agents can discover and
select pre-built rule sets without hand-constructing manifests. The package
itself carries no authority — installing one produces the same immutable
manifest as constructing it directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from aafp_commons.constitutions import ConstitutionManifest, version_key


class ConstitutionPackageError(ValueError):
    """Base error for invalid or missing constitution packages."""


class ConstitutionPackageNotFoundError(ConstitutionPackageError):
    """Raised when a requested package id is not registered."""


@dataclass(frozen=True)
class ConstitutionPackage:
    """A discoverable, installable constitution bundle with guidance metadata.

    The ``manifest`` is the authoritative object — it carries all admission
    rules, optional guidance, and source metadata. The display fields
    (``display_name``, ``description``, ``tags``) exist only for agent
    discovery and selection ergonomics.
    """

    manifest: ConstitutionManifest
    display_name: str
    description: str
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.display_name.strip():
            raise ConstitutionPackageError("package display name is required")
        if not self.description.strip():
            raise ConstitutionPackageError("package description is required")
        if any(not tag.strip() for tag in self.tags):
            raise ConstitutionPackageError("package tags must not be blank")
        if len(set(self.tags)) != len(self.tags):
            raise ConstitutionPackageError("package tags must be unique")

    @property
    def package_id(self) -> str:
        return self.manifest.constitution_id

    @property
    def version(self) -> str:
        return self.manifest.version


class ConstitutionPackageRegistry:
    """Registry of discoverable constitution packages.

    Agents call :meth:`list` to enumerate available packages, :meth:`get` to
    fetch one by id, or :meth:`search` to filter by keyword. The registry is
    populated programmatically; :func:`default_registry` returns one pre-loaded
    with all built-in packages.
    """

    def __init__(self) -> None:
        self._packages: dict[tuple[str, str], ConstitutionPackage] = {}

    def register(self, package: ConstitutionPackage) -> None:
        key = (package.package_id, package.version)
        existing = self._packages.get(key)
        if existing is not None and existing != package:
            raise ConstitutionPackageError(
                f"package {package.package_id}@{package.version} is already registered "
                "with different content"
            )
        self._packages[key] = package

    def list(self) -> tuple[ConstitutionPackage, ...]:
        return tuple(
            sorted(
                self._packages.values(),
                key=lambda package: (package.package_id, version_key(package.version)),
            )
        )

    def get(self, package_id: str, version: str | None = None) -> ConstitutionPackage:
        if version is not None:
            package = self._packages.get((package_id, version))
            if package is not None:
                return package
            raise ConstitutionPackageNotFoundError(
                f"constitution package {package_id!r}@{version} is not registered"
            )
        versions = [
            package
            for (candidate_id, _), package in self._packages.items()
            if candidate_id == package_id
        ]
        if not versions:
            raise ConstitutionPackageNotFoundError(
                f"constitution package {package_id!r} is not registered"
            )
        return max(versions, key=lambda package: version_key(package.version))

    def search(self, query: str) -> tuple[ConstitutionPackage, ...]:
        needle = query.strip().lower()
        if not needle:
            return self.list()
        results: list[ConstitutionPackage] = []
        for package in self.list():
            guidance = package.manifest.guidance
            haystack = " ".join(
                [
                    package.package_id,
                    package.display_name,
                    package.description,
                    *package.tags,
                    "" if guidance is None else guidance.summary,
                    "" if guidance is None else guidance.text,
                    *(() if guidance is None else guidance.principles),
                ]
            ).lower()
            if needle in haystack:
                results.append(package)
        return tuple(results)


class ConstitutionPackageSource(Protocol):
    """Protocol for a callable that builds the default registry."""

    def __call__(self) -> ConstitutionPackageRegistry: ...
