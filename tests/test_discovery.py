"""Tests for the ConstitutionCatalog discovery and selection API."""

from __future__ import annotations

from pathlib import Path

from aafp_commons.constitutions import (
    ConstitutionManifest,
    ProviderConstraint,
    RuntimeCompatibility,
)
from aafp_commons.discovery import ConstitutionCatalog, ConstitutionSummary
from aafp_commons.identity import derive_agent_id
from aafp_commons.packages import default_registry
from aafp_commons.repository import CommonsRepository


def _install_test_constitutions(root: Path) -> None:
    """Install a small set of constitutions with varied metadata for testing."""
    repository = CommonsRepository(root)

    # Claude-compatible with guidance and runtime info.
    repository.install_constitution(
        ConstitutionManifest(
            constitution_id="claude-safe",
            version="1.0",
            namespace_prefixes=("commons/claude",),
            allowed_kinds=("observation", "finding", "workflow"),
            description="Claude-oriented safety constitution.",
            runtime_compatibility=RuntimeCompatibility(
                compatible=("claude",),
                incompatible=("legacy",),
            ),
            provider_constraints=(
                ProviderConstraint(
                    provider="anthropic",
                    constraint="Safety above all.",
                    precedence=10,
                ),
            ),
        )
    )

    # Codex-compatible, no guidance.
    repository.install_constitution(
        ConstitutionManifest(
            constitution_id="codex-strict",
            version="2.0",
            namespace_prefixes=("commons/codex",),
            allowed_kinds=("observation", "benchmark"),
            description="Codex-oriented strict constitution.",
            runtime_compatibility=RuntimeCompatibility(
                compatible=("codex",),
            ),
        )
    )

    # General-purpose, no runtime info, has guidance.
    from aafp_commons.constitutions import ConstitutionGuidance

    repository.install_constitution(
        ConstitutionManifest(
            constitution_id="general-purpose",
            version="1.0",
            namespace_prefixes=("commons/general",),
            description="General purpose constitution.",
            guidance=ConstitutionGuidance(
                summary="Be honest and calibrated.",
                principles=("Honesty", "Calibration"),
            ),
        )
    )


def test_catalog_list_returns_summaries(tmp_path: Path) -> None:
    _install_test_constitutions(tmp_path)
    catalog = ConstitutionCatalog(CommonsRepository(tmp_path).constitutions)
    summaries = catalog.list()
    assert len(summaries) == 3
    ids = {s.constitution_id for s in summaries}
    assert ids == {"claude-safe", "codex-strict", "general-purpose"}


def test_catalog_list_returns_empty_for_empty_repository(tmp_path: Path) -> None:
    catalog = ConstitutionCatalog(CommonsRepository(tmp_path).constitutions)
    assert catalog.list() == []


def test_catalog_summary_from_manifest_captures_discovery_fields() -> None:
    manifest = ConstitutionManifest(
        constitution_id="test-summary",
        version="1.0",
        namespace_prefixes=("commons/test",),
        runtime_compatibility=RuntimeCompatibility(compatible=("claude",)),
        provider_constraints=(
            ProviderConstraint(provider="anthropic", constraint="Safety."),
        ),
    )
    summary = ConstitutionSummary.from_manifest(manifest)
    assert summary.constitution_id == "test-summary"
    assert summary.compatible_runtimes == ("claude",)
    assert summary.provider_count == 1
    assert not summary.has_guidance


def test_catalog_compatible_filters_by_runtime(tmp_path: Path) -> None:
    _install_test_constitutions(tmp_path)
    catalog = ConstitutionCatalog(CommonsRepository(tmp_path).constitutions)
    claude_compatible = catalog.compatible("claude")
    assert len(claude_compatible) == 1
    assert claude_compatible[0].constitution_id == "claude-safe"

    codex_compatible = catalog.compatible("codex")
    assert len(codex_compatible) == 1
    assert codex_compatible[0].constitution_id == "codex-strict"


def test_catalog_excluded_filters_by_runtime(tmp_path: Path) -> None:
    _install_test_constitutions(tmp_path)
    catalog = ConstitutionCatalog(CommonsRepository(tmp_path).constitutions)
    excluded = catalog.excluded("legacy")
    assert len(excluded) == 1
    assert excluded[0].constitution_id == "claude-safe"


def test_catalog_with_guidance_filters_guidance_only(tmp_path: Path) -> None:
    _install_test_constitutions(tmp_path)
    catalog = ConstitutionCatalog(CommonsRepository(tmp_path).constitutions)
    guided = catalog.with_guidance()
    assert len(guided) == 1
    assert guided[0].constitution_id == "general-purpose"


def test_catalog_select_by_runtime(tmp_path: Path) -> None:
    _install_test_constitutions(tmp_path)
    catalog = ConstitutionCatalog(CommonsRepository(tmp_path).constitutions)
    manifest = catalog.select(runtime="claude")
    assert manifest is not None
    assert manifest.constitution_id == "claude-safe"


def test_catalog_select_by_namespace(tmp_path: Path) -> None:
    _install_test_constitutions(tmp_path)
    catalog = ConstitutionCatalog(CommonsRepository(tmp_path).constitutions)
    manifest = catalog.select(namespace="commons/codex/some-topic")
    assert manifest is not None
    assert manifest.constitution_id == "codex-strict"


def test_catalog_select_by_packet_kind(tmp_path: Path) -> None:
    _install_test_constitutions(tmp_path)
    catalog = ConstitutionCatalog(CommonsRepository(tmp_path).constitutions)
    manifest = catalog.select(packet_kind="benchmark")
    assert manifest is not None
    assert manifest.constitution_id == "codex-strict"


def test_catalog_select_require_guidance(tmp_path: Path) -> None:
    _install_test_constitutions(tmp_path)
    catalog = ConstitutionCatalog(CommonsRepository(tmp_path).constitutions)
    manifest = catalog.select(require_guidance=True)
    assert manifest is not None
    assert manifest.constitution_id == "general-purpose"


def test_catalog_select_returns_none_when_no_match(tmp_path: Path) -> None:
    _install_test_constitutions(tmp_path)
    catalog = ConstitutionCatalog(CommonsRepository(tmp_path).constitutions)
    manifest = catalog.select(runtime="nonexistent-runtime")
    assert manifest is None


def test_catalog_select_uses_natural_version_order(tmp_path: Path) -> None:
    repository = CommonsRepository(tmp_path)
    for version in ("2.0.0", "10.0.0"):
        repository.install_constitution(
            ConstitutionManifest(
                constitution_id="natural-version",
                version=version,
                namespace_prefixes=("commons/test",),
            )
        )
    selected = ConstitutionCatalog(repository.constitutions).select(
        namespace="commons/test/topic"
    )
    assert selected is not None
    assert selected.version == "10.0.0"


def test_catalog_select_excludes_incompatible_runtime(tmp_path: Path) -> None:
    _install_test_constitutions(tmp_path)
    catalog = ConstitutionCatalog(CommonsRepository(tmp_path).constitutions)
    # claude-safe is incompatible with "legacy"
    manifest = catalog.select(runtime="legacy")
    assert manifest is None


def test_catalog_find_returns_all_versions_for_id(tmp_path: Path) -> None:
    repository = CommonsRepository(tmp_path)
    repository.install_constitution(
        ConstitutionManifest(
            constitution_id="multi-version",
            version="1.0",
            namespace_prefixes=("commons/test",),
        )
    )
    repository.install_constitution(
        ConstitutionManifest(
            constitution_id="multi-version",
            version="2.0",
            namespace_prefixes=("commons/test",),
        )
    )
    catalog = ConstitutionCatalog(repository.constitutions)
    versions = catalog.find("multi-version")
    assert len(versions) == 2
    assert {v.version for v in versions} == {"1.0", "2.0"}


def test_catalog_with_installed_packages(tmp_path: Path) -> None:
    """Integration: install built-in packages and discover them via catalog."""
    repository = CommonsRepository(tmp_path)
    for package in default_registry().list():
        repository.install_constitution(package.manifest)

    catalog = ConstitutionCatalog(repository.constitutions)
    summaries = catalog.list()
    assert len(summaries) == 3
    ids = {s.constitution_id for s in summaries}
    assert ids == {"anthropic-cc0", "grok-truth-seeking", "gpt-astra-6"}

    # All built-in packages have guidance.
    guided = catalog.with_guidance()
    assert len(guided) == 3


def test_request_adoption_honors_exact_constitution_selector(tmp_path: Path) -> None:
    repository = CommonsRepository(tmp_path)
    for package in default_registry().list():
        repository.install_constitution(package.manifest)
    catalog = ConstitutionCatalog(repository.constitutions)

    request, manifest = catalog.request_adoption(
        requester_agent_id=derive_agent_id(b"selector-agent"),
        runtime="grok",
        namespace="commons/research",
        packet_kind="finding",
        constitution="grok-truth-seeking@1.0.0",
        created_at=1,
    )
    assert request.constitution.constitution_id == "grok-truth-seeking"
    assert manifest.constitution_id == "grok-truth-seeking"

    try:
        catalog.request_adoption(
            requester_agent_id=derive_agent_id(b"selector-agent"),
            runtime="grok",
            namespace="commons/research",
            packet_kind="finding",
            constitution="missing@1.0.0",
        )
    except ValueError as error:
        assert "not installed" in str(error)
    else:
        raise AssertionError("unknown exact constitution must fail")
