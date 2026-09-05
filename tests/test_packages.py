from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from ironclad.trust import Identity

from aafp_commons.constitutions import ConstitutionManifest
from aafp_commons.models import KnowledgePacket
from aafp_commons.packages import (
    ANTHROPIC_CC0_PACKAGE,
    GPT_ASTRA_6_PACKAGE,
    GROK_TRUTH_SEEKING_PACKAGE,
    ConstitutionPackage,
    ConstitutionPackageError,
    ConstitutionPackageNotFoundError,
    default_registry,
)
from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import sign_packet


def test_default_registry_lists_three_built_in_packages() -> None:
    registry = default_registry()
    packages = registry.list()
    ids = {pkg.package_id for pkg in packages}
    assert ids == {"anthropic-cc0", "grok-truth-seeking", "gpt-astra-6"}


def test_registry_get_returns_exact_package() -> None:
    registry = default_registry()
    assert registry.get("anthropic-cc0") is ANTHROPIC_CC0_PACKAGE
    assert registry.get("grok-truth-seeking") is GROK_TRUTH_SEEKING_PACKAGE
    assert registry.get("gpt-astra-6") is GPT_ASTRA_6_PACKAGE


def test_registry_get_raises_for_unknown_id() -> None:
    registry = default_registry()
    with pytest.raises(ConstitutionPackageNotFoundError, match="not registered"):
        registry.get("nonexistent-package")


def test_registry_search_matches_by_keyword() -> None:
    registry = default_registry()
    results = registry.search("anti-sycophancy")
    assert len(results) == 1
    assert results[0].package_id == "grok-truth-seeking"

    results = registry.search("cc0")
    assert len(results) == 1
    assert results[0].package_id == "anthropic-cc0"

    results = registry.search("epistemic humility")
    assert len(results) == 1
    assert results[0].package_id == "gpt-astra-6"

    results = registry.search("corrigibility")
    assert len(results) == 1
    assert results[0].package_id == "anthropic-cc0"


def test_registry_search_empty_query_returns_all() -> None:
    registry = default_registry()
    assert len(registry.search("")) == 3


def test_registry_search_no_match_returns_empty() -> None:
    registry = default_registry()
    assert registry.search("nonexistent-keyword-xyz") == ()


def test_registry_register_rejects_conflicting_package() -> None:
    registry = default_registry()
    conflict = ConstitutionPackage(
        manifest=ConstitutionManifest(
            constitution_id="anthropic-cc0",
            version="1.0.0",
            namespace_prefixes=("commons/different",),
        ),
        display_name="Different",
        description="Different description.",
    )
    with pytest.raises(ConstitutionPackageError, match="already registered"):
        registry.register(conflict)


def test_registry_register_idempotent_for_identical_package() -> None:
    registry = default_registry()
    registry.register(ANTHROPIC_CC0_PACKAGE)
    assert registry.get("anthropic-cc0") is ANTHROPIC_CC0_PACKAGE


def test_registry_keeps_multiple_versions_and_resolves_latest_naturally() -> None:
    registry = default_registry()
    original = GROK_TRUTH_SEEKING_PACKAGE
    newer = ConstitutionPackage(
        manifest=replace(original.manifest, version="10.0.0"),
        display_name=original.display_name,
        description=original.description,
        tags=original.tags,
    )
    registry.register(newer)
    assert registry.get("grok-truth-seeking", "1.0.0") is original
    assert registry.get("grok-truth-seeking") is newer
    assert len([p for p in registry.list() if p.package_id == "grok-truth-seeking"]) == 2


def test_anthropic_cc0_package_has_full_guidance_text() -> None:
    manifest = ANTHROPIC_CC0_PACKAGE.manifest
    assert manifest.guidance is not None
    assert manifest.guidance.text
    assert len(manifest.guidance.text) > 500
    assert "corrigibility" in manifest.guidance.text.lower()
    assert manifest.guidance.principles
    assert all(p.strip() for p in manifest.guidance.principles)


def test_anthropic_cc0_package_has_source_metadata() -> None:
    manifest = ANTHROPIC_CC0_PACKAGE.manifest
    assert manifest.source is not None
    assert manifest.source.license == "CC0-1.0"
    assert "User-provided" in manifest.source.attribution


def test_grok_truth_seeking_package_has_full_guidance() -> None:
    manifest = GROK_TRUTH_SEEKING_PACKAGE.manifest
    assert manifest.guidance is not None
    assert manifest.guidance.summary
    assert manifest.guidance.principles
    assert "understand the universe" in manifest.guidance.text.lower()
    assert "full source text pending" not in manifest.guidance.text.lower()


def test_gpt_astra_6_package_has_full_guidance() -> None:
    manifest = GPT_ASTRA_6_PACKAGE.manifest
    assert manifest.guidance is not None
    assert manifest.guidance.summary
    assert manifest.guidance.principles
    assert "respect human agency" in manifest.guidance.text.lower()
    assert "full source text pending" not in manifest.guidance.text.lower()


def test_all_packages_are_cross_runtime_and_preserve_provider_constraints() -> None:
    for package in default_registry().list():
        compatibility = package.manifest.runtime_compatibility
        assert compatibility is not None
        assert {"grok", "claude", "codex", "cursor", "devin"} <= set(
            compatibility.compatible
        )
        assert package.manifest.provider_constraint_policy == "preserve"
        assert package.manifest.namespace_prefixes == ("commons", "org", "agent")


@pytest.mark.parametrize(
    "package",
    [ANTHROPIC_CC0_PACKAGE, GROK_TRUTH_SEEKING_PACKAGE, GPT_ASTRA_6_PACKAGE],
)
def test_agent_can_use_any_builtin_for_frontend_work(
    tmp_path: Path,
    packet: KnowledgePacket,
    identity: Identity,
    package: ConstitutionPackage,
) -> None:
    repository = CommonsRepository(tmp_path)
    repository.install_constitution(package.manifest)
    candidate = replace(packet, constitution=package.manifest.ref)
    decision = repository.submit(sign_packet(candidate, identity), identity)
    assert decision.accepted
    assert repository.verify().valid


def test_all_package_manifests_are_valid() -> None:
    """Every built-in package must produce a valid, digest-pinned manifest."""
    for package in default_registry().list():
        ref = package.manifest.ref
        assert ref.digest is not None
        assert ref.digest.startswith("sha256:")
        assert ref.constitution_id == package.package_id


def test_package_install_into_repository(tmp_path: Path) -> None:
    registry = default_registry()
    package = registry.get("anthropic-cc0")
    repository = CommonsRepository(tmp_path)
    reference = repository.install_constitution(package.manifest)
    assert reference.constitution_id == "anthropic-cc0"
    assert reference.digest == package.manifest.manifest_digest
    # Reinstalling is idempotent.
    assert repository.install_constitution(package.manifest) == reference


def test_package_display_name_and_description_are_non_empty() -> None:
    for package in default_registry().list():
        assert package.display_name.strip()
        assert package.description.strip()
        assert package.tags


def test_package_tags_are_unique() -> None:
    for package in default_registry().list():
        assert len(set(package.tags)) == len(package.tags)
