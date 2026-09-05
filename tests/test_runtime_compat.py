"""Tests for runtime compatibility, provider constraints, and manifest extensions."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from aafp_commons.constitutions import (
    ConstitutionError,
    ConstitutionManifest,
    FileConstitutionResolver,
    ProviderConstraint,
    RuntimeCompatibility,
    constraints_by_precedence,
    merge_constraints,
)

# --- RuntimeCompatibility ---


def test_runtime_compatibility_defaults_are_empty() -> None:
    rc = RuntimeCompatibility()
    assert rc.compatible == ()
    assert rc.incompatible == ()
    assert rc.notes == ""
    assert not rc.is_restricted
    assert rc.is_compatible("claude") is None


def test_runtime_compatibility_is_compatible_returns_true_false_none() -> None:
    rc = RuntimeCompatibility(
        compatible=("claude", "codex"),
        incompatible=("legacy-runtime",),
    )
    assert rc.is_compatible("claude") is True
    assert rc.is_compatible("codex") is True
    assert rc.is_compatible("legacy-runtime") is False
    assert rc.is_compatible("unknown-runtime") is None
    assert rc.is_restricted


def test_runtime_compatibility_rejects_overlap() -> None:
    with pytest.raises(ConstitutionError, match="both compatible and incompatible"):
        RuntimeCompatibility(
            compatible=("claude",),
            incompatible=("claude",),
        )


def test_runtime_compatibility_rejects_duplicate_compatible() -> None:
    with pytest.raises(ConstitutionError, match="compatible runtimes must be unique"):
        RuntimeCompatibility(compatible=("claude", "claude"))


def test_runtime_compatibility_rejects_invalid_identifier() -> None:
    with pytest.raises(ConstitutionError, match="compatible runtime identifier is invalid"):
        RuntimeCompatibility(compatible=("CLAUDE",))


def test_runtime_compatibility_round_trips() -> None:
    rc = RuntimeCompatibility(
        compatible=("claude", "codex"),
        incompatible=("legacy",),
        notes="Tested with Claude 4.5 and Codex 1.0.",
    )
    rebuilt = RuntimeCompatibility.from_dict(rc.to_dict())
    assert rebuilt == rc


# --- ProviderConstraint ---


def test_provider_constraint_requires_provider_and_constraint() -> None:
    with pytest.raises(ConstitutionError, match="provider is required"):
        ProviderConstraint(provider="", constraint="safety-first")
    with pytest.raises(ConstitutionError, match="constraint text is required"):
        ProviderConstraint(provider="anthropic", constraint="")


def test_provider_constraint_rejects_invalid_provider_identifier() -> None:
    with pytest.raises(ConstitutionError, match="safe identifier"):
        ProviderConstraint(provider="Anthropic", constraint="safety-first")


def test_provider_constraint_round_trips() -> None:
    pc = ProviderConstraint(
        provider="anthropic",
        constraint="Safety above all else.",
        precedence=10,
        source_url="https://example.test/policy",
    )
    rebuilt = ProviderConstraint.from_dict(pc.to_dict())
    assert rebuilt == pc


# --- constraints_by_precedence / merge_constraints ---


def test_constraints_by_precedence_sorts_descending() -> None:
    constraints = (
        ProviderConstraint(provider="operator", constraint="A", precedence=1),
        ProviderConstraint(provider="anthropic", constraint="B", precedence=10),
        ProviderConstraint(provider="openai", constraint="C", precedence=5),
    )
    ordered = constraints_by_precedence(constraints)
    assert ordered[0].precedence == 10
    assert ordered[1].precedence == 5
    assert ordered[2].precedence == 1


def test_constraints_by_precedence_ties_break_by_provider_name() -> None:
    constraints = (
        ProviderConstraint(provider="zzz", constraint="A", precedence=5),
        ProviderConstraint(provider="aaa", constraint="B", precedence=5),
    )
    ordered = constraints_by_precedence(constraints)
    assert ordered[0].provider == "aaa"
    assert ordered[1].provider == "zzz"


def test_merge_constraints_collapses_duplicates_to_highest_precedence() -> None:
    group_a = (
        ProviderConstraint(provider="anthropic", constraint="Safety first.", precedence=5),
    )
    group_b = (
        ProviderConstraint(provider="anthropic", constraint="Safety first.", precedence=10),
    )
    merged = merge_constraints(group_a, group_b)
    assert len(merged) == 1
    assert merged[0].precedence == 10


def test_merge_constraints_preserves_distinct_entries() -> None:
    group_a = (
        ProviderConstraint(provider="anthropic", constraint="Safety first.", precedence=10),
    )
    group_b = (
        ProviderConstraint(provider="operator", constraint="No exfiltration.", precedence=5),
    )
    merged = merge_constraints(group_a, group_b)
    assert len(merged) == 2
    assert merged[0].precedence == 10  # anthropic first (higher precedence)
    assert merged[1].precedence == 5


# --- ConstitutionManifest with new fields ---


def test_manifest_with_runtime_compatibility_and_constraints_round_trips() -> None:
    manifest = ConstitutionManifest(
        constitution_id="runtime-aware",
        version="1.0",
        namespace_prefixes=("commons/test",),
        runtime_compatibility=RuntimeCompatibility(
            compatible=("claude", "codex"),
            incompatible=("legacy",),
        ),
        provider_constraints=(
            ProviderConstraint(
                provider="anthropic",
                constraint="Safety above ethics.",
                precedence=10,
            ),
            ProviderConstraint(
                provider="operator",
                constraint="No data exfiltration.",
                precedence=5,
            ),
        ),
    )
    rebuilt = ConstitutionManifest.from_dict(manifest.to_dict())
    assert rebuilt == manifest
    assert rebuilt.runtime_compatibility is not None
    assert rebuilt.runtime_compatibility.compatible == ("claude", "codex")
    assert len(rebuilt.provider_constraints) == 2
    assert rebuilt.provider_constraints[0].provider == "anthropic"


def test_manifest_without_new_fields_defaults_to_none_and_empty() -> None:
    manifest = ConstitutionManifest(
        constitution_id="minimal",
        version="1.0",
        namespace_prefixes=("commons/test",),
    )
    assert manifest.runtime_compatibility is None
    assert manifest.provider_constraints == ()
    assert manifest.provider_constraint_policy == "preserve"


def test_manifest_cannot_override_provider_constraints() -> None:
    with pytest.raises(ConstitutionError, match="preserve provider constraints"):
        ConstitutionManifest(
            constitution_id="unsafe-override",
            version="1.0",
            namespace_prefixes=("commons/test",),
            provider_constraint_policy="override",  # type: ignore[arg-type]
        )


def test_manifest_rejects_duplicate_provider_constraint_entries() -> None:
    with pytest.raises(ConstitutionError, match="entries must be unique"):
        ConstitutionManifest(
            constitution_id="dup-providers",
            version="1.0",
            namespace_prefixes=("commons/test",),
            provider_constraints=(
                ProviderConstraint(provider="anthropic", constraint="A", precedence=1),
                ProviderConstraint(provider="anthropic", constraint="A", precedence=2),
            ),
        )


def test_manifest_allows_multiple_distinct_constraints_from_one_provider() -> None:
    manifest = ConstitutionManifest(
        constitution_id="multi-provider-rules",
        version="1.0",
        namespace_prefixes=("commons/test",),
        provider_constraints=(
            ProviderConstraint(provider="anthropic", constraint="A", precedence=1),
            ProviderConstraint(provider="anthropic", constraint="B", precedence=2),
        ),
    )
    assert len(manifest.provider_constraints) == 2


def test_manifest_with_new_fields_is_immutable_after_install(tmp_path: Path) -> None:
    manifest = ConstitutionManifest(
        constitution_id="immutable-ext",
        version="1.0",
        namespace_prefixes=("commons/test",),
        runtime_compatibility=RuntimeCompatibility(compatible=("claude",)),
        provider_constraints=(
            ProviderConstraint(provider="anthropic", constraint="Safety first."),
        ),
    )
    resolver = FileConstitutionResolver(tmp_path)
    resolver.install(manifest)
    path = tmp_path / "immutable-ext" / "1.0.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["runtime_compatibility"]["compatible"] = ["codex"]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception, match="digest"):
        resolver.resolve(manifest.ref)


def test_runtime_compatibility_does_not_affect_admission(
    tmp_path: Path,
    packet: object,
    identity: object,
    constitution: ConstitutionManifest,
) -> None:
    """Runtime compatibility is advisory only — it must not change admission."""
    from aafp_commons.repository import CommonsRepository
    from aafp_commons.signing import sign_packet

    extended = replace(
        constitution,
        constitution_id="frontier-dev-rc",
        runtime_compatibility=RuntimeCompatibility(compatible=("claude",)),
    )
    repository = CommonsRepository(tmp_path)
    repository.install_constitution(extended)
    extended_packet = replace(packet, constitution=extended.ref)  # type: ignore[attr-defined]
    decision = repository.submit(sign_packet(extended_packet, identity), identity)  # type: ignore[arg-type]
    assert decision.accepted


# --- FileConstitutionResolver.list() and .find() ---


def test_resolver_list_returns_empty_for_nonexistent_root(tmp_path: Path) -> None:
    resolver = FileConstitutionResolver(tmp_path / "nonexistent")
    assert resolver.list() == []


def test_resolver_list_returns_all_installed_manifests(tmp_path: Path) -> None:
    resolver = FileConstitutionResolver(tmp_path)
    m1 = ConstitutionManifest(
        constitution_id="alpha",
        version="1.0",
        namespace_prefixes=("commons/alpha",),
    )
    m2 = ConstitutionManifest(
        constitution_id="beta",
        version="2.0",
        namespace_prefixes=("commons/beta",),
    )
    resolver.install(m1)
    resolver.install(m2)
    manifests = resolver.list()
    assert len(manifests) == 2
    ids = {m.constitution_id for m in manifests}
    assert ids == {"alpha", "beta"}


def test_resolver_find_returns_all_versions_of_one_id(tmp_path: Path) -> None:
    resolver = FileConstitutionResolver(tmp_path)
    v1 = ConstitutionManifest(
        constitution_id="versioned",
        version="1.0",
        namespace_prefixes=("commons/test",),
    )
    v2 = ConstitutionManifest(
        constitution_id="versioned",
        version="2.0",
        namespace_prefixes=("commons/test",),
    )
    other = ConstitutionManifest(
        constitution_id="other",
        version="1.0",
        namespace_prefixes=("commons/other",),
    )
    resolver.install(v1)
    resolver.install(v2)
    resolver.install(other)
    versions = resolver.find("versioned")
    assert len(versions) == 2
    assert {m.version for m in versions} == {"1.0", "2.0"}


def test_resolver_find_returns_empty_for_unknown_id(tmp_path: Path) -> None:
    resolver = FileConstitutionResolver(tmp_path)
    assert resolver.find("nonexistent") == []


def test_resolver_find_rejects_invalid_id(tmp_path: Path) -> None:
    resolver = FileConstitutionResolver(tmp_path)
    with pytest.raises(ConstitutionError, match="safe identifier"):
        resolver.find("INVALID")
