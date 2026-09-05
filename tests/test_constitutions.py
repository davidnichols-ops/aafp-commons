from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from ironclad.trust import Identity

from aafp_commons.constitutions import (
    ConstitutionGuidance,
    ConstitutionIntegrityError,
    ConstitutionManifest,
    ConstitutionNotFoundError,
    ConstitutionSource,
    FileConstitutionResolver,
)
from aafp_commons.models import ConstitutionRef, KnowledgePacket
from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import sign_packet


def test_manifest_round_trip_and_reference_are_content_addressed(
    constitution: ConstitutionManifest,
) -> None:
    rebuilt = ConstitutionManifest.from_dict(constitution.to_dict())
    assert rebuilt == constitution
    assert rebuilt.ref.digest == constitution.manifest_digest
    assert rebuilt.ref.constitution_id == "frontier-dev"
    assert rebuilt.ref.version == "0.1"


def test_resolver_installs_exact_versions_without_mutation(
    tmp_path: Path, constitution: ConstitutionManifest
) -> None:
    resolver = FileConstitutionResolver(tmp_path)
    reference = resolver.install(constitution)
    assert resolver.resolve(reference) == constitution
    assert resolver.install(constitution) == reference

    changed = replace(constitution, minimum_evidence=2)
    with pytest.raises(ConstitutionIntegrityError, match="already exists"):
        resolver.install(changed)


def test_resolver_rejects_missing_and_digest_mismatched_versions(
    tmp_path: Path, constitution: ConstitutionManifest
) -> None:
    resolver = FileConstitutionResolver(tmp_path)
    with pytest.raises(ConstitutionNotFoundError, match="not installed"):
        resolver.resolve(constitution.ref)

    resolver.install(constitution)
    wrong_digest = ConstitutionRef(
        constitution.constitution_id,
        constitution.version,
        "sha256:" + "0" * 64,
    )
    with pytest.raises(ConstitutionIntegrityError, match="digest"):
        resolver.resolve(wrong_digest)


def test_admission_fails_closed_for_unresolved_or_unpinned_constitution(
    tmp_path: Path,
    packet: KnowledgePacket,
    identity: Identity,
    constitution: ConstitutionManifest,
) -> None:
    repository = CommonsRepository(tmp_path)
    unresolved = repository.submit(sign_packet(packet, identity), identity)
    assert not unresolved.accepted
    assert "not installed" in unresolved.reasons[0]
    repository.install_constitution(constitution)
    unpinned_packet = replace(
        packet,
        constitution=ConstitutionRef(constitution.constitution_id, constitution.version),
    )
    unpinned = repository.submit(sign_packet(unpinned_packet, identity), identity)
    assert not unpinned.accepted
    assert "must pin" in unpinned.reasons[0]


def test_manifest_json_round_trip_is_canonical(tmp_path: Path) -> None:
    manifest = ConstitutionManifest(
        constitution_id="portable",
        version="1.0.0",
        namespace_prefixes=("commons/research",),
    )
    encoded = manifest.to_json()
    assert encoded.endswith("\n")
    assert ConstitutionManifest.from_json(encoded) == manifest
    resolver = FileConstitutionResolver(tmp_path)
    assert resolver.install_json(encoded) == manifest.ref

def test_constitution_rules_participate_in_admission_without_granting_authority(
    tmp_path: Path,
    packet: KnowledgePacket,
    identity: Identity,
) -> None:
    strict = ConstitutionManifest(
        constitution_id="strict-reproductions",
        version="1.0.0",
        namespace_prefixes=("commons/backend",),
        allowed_kinds=("benchmark",),
        required_evidence_kinds=("benchmark-report",),
        require_evidence_digests=True,
    )
    candidate = replace(packet, constitution=strict.ref)
    repository = CommonsRepository(tmp_path)
    repository.install_constitution(strict)
    decision = repository.submit(sign_packet(candidate, identity), identity)
    assert not decision.accepted
    assert set(decision.reasons) == {
        "packet namespace is outside the constitution scope",
        "packet kind is not allowed by the constitution",
        "constitution requires evidence kinds: benchmark-report",
        "constitution requires content-addressed evidence",
    }
    assert not repository.object_path(candidate.packet_id).exists()


def test_repository_verification_detects_manifest_tampering(
    tmp_path: Path,
    packet: KnowledgePacket,
    identity: Identity,
    constitution: ConstitutionManifest,
) -> None:
    repository = CommonsRepository(tmp_path)
    repository.install_constitution(constitution)
    assert repository.submit(sign_packet(packet, identity), identity).accepted

    path = (
        tmp_path
        / "constitutions"
        / constitution.constitution_id
        / f"{constitution.version}.json"
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    data["minimum_evidence"] = 2
    path.write_text(json.dumps(data), encoding="utf-8")
    result = repository.verify()
    assert not result.valid
    assert any("digest does not match" in error for error in result.errors)


def test_resolver_listing_rejects_manifest_at_wrong_path(
    tmp_path: Path, constitution: ConstitutionManifest
) -> None:
    wrong_dir = tmp_path / "wrong-id"
    wrong_dir.mkdir()
    (wrong_dir / "9.9.json").write_text(
        json.dumps(constitution.to_dict()),
        encoding="utf-8",
    )
    with pytest.raises(ConstitutionIntegrityError, match="identity does not match"):
        FileConstitutionResolver(tmp_path).list()


# --- Guidance and source metadata tests ---


def test_manifest_with_guidance_and_source_round_trips() -> None:
    manifest = ConstitutionManifest(
        constitution_id="guided-test",
        version="1.0",
        namespace_prefixes=("commons/test",),
        guidance=ConstitutionGuidance(
            summary="Be honest and calibrated.",
            principles=("Truthfulness", "Calibration"),
            text="Full guidance text here.",
        ),
        source=ConstitutionSource(
            title="Test Constitution",
            url="https://example.test/constitution",
            license="CC0-1.0",
            attribution="Test Author",
        ),
    )
    rebuilt = ConstitutionManifest.from_dict(manifest.to_dict())
    assert rebuilt == manifest
    assert rebuilt.guidance is not None
    assert rebuilt.guidance.summary == "Be honest and calibrated."
    assert rebuilt.guidance.principles == ("Truthfulness", "Calibration")
    assert rebuilt.source is not None
    assert rebuilt.source.license == "CC0-1.0"


def test_manifest_without_guidance_and_source_defaults_to_none(
    constitution: ConstitutionManifest,
) -> None:
    assert constitution.guidance is None
    assert constitution.source is None
    rebuilt = ConstitutionManifest.from_dict(constitution.to_dict())
    assert rebuilt.guidance is None
    assert rebuilt.source is None


def test_guidance_with_duplicate_principles_is_rejected() -> None:
    with pytest.raises(ValueError, match="principles must be unique"):
        ConstitutionGuidance(principles=("Honesty", "Honesty"))


def test_guidance_with_blank_principle_is_rejected() -> None:
    with pytest.raises(ValueError, match="principles must not be blank"):
        ConstitutionGuidance(principles=("Honesty", "  "))


def test_source_with_blank_license_is_rejected() -> None:
    with pytest.raises(ValueError, match="source license must not be blank"):
        ConstitutionSource(license="  ")


def test_guidance_does_not_affect_admission_decisions(
    tmp_path: Path,
    packet: KnowledgePacket,
    identity: Identity,
    constitution: ConstitutionManifest,
) -> None:
    """Guidance is advisory only — it must not change admission outcomes."""
    guided = replace(
        constitution,
        constitution_id="frontier-dev-guided",
        guidance=ConstitutionGuidance(
            summary="Be extra careful.",
            principles=("Caution",),
            text="Some long guidance text.",
        ),
    )
    repository = CommonsRepository(tmp_path)
    repository.install_constitution(guided)
    guided_packet = replace(packet, constitution=guided.ref)
    decision = repository.submit(sign_packet(guided_packet, identity), identity)
    assert decision.accepted
    # The same packet under the unguided constitution should also be admissible
    # (both have the same admission rules, just different guidance).
    repository.install_constitution(constitution)
    unguided_decision = repository.submit(sign_packet(packet, identity), identity)
    assert unguided_decision.accepted


def test_guidance_and_source_are_immutable_after_install(
    tmp_path: Path,
) -> None:
    manifest = ConstitutionManifest(
        constitution_id="immutable-guidance",
        version="1.0",
        namespace_prefixes=("commons/test",),
        guidance=ConstitutionGuidance(summary="Original guidance."),
        source=ConstitutionSource(title="Original source", license="MIT"),
    )
    resolver = FileConstitutionResolver(tmp_path)
    resolver.install(manifest)

    # Tampering with guidance text must break the digest check.
    path = tmp_path / "immutable-guidance" / "1.0.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["guidance"]["summary"] = "Tampered guidance."
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ConstitutionIntegrityError, match="digest"):
        resolver.resolve(manifest.ref)


def test_repository_ships_portable_builtin_manifests() -> None:
    from aafp_commons.packages import default_registry

    root = Path(__file__).parents[1] / "constitutions"
    for package in default_registry().list():
        path = root / package.package_id / f"{package.version}.json"
        assert path.exists()
        restored = ConstitutionManifest.from_json(path.read_text(encoding="utf-8"))
        assert restored == package.manifest
