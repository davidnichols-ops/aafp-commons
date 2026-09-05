"""Regression test: built-in constitution JSON ships in the package and is digest-addressed.

Guards the hatch ``force-include`` that bundles ``constitutions/`` into the
wheel. If the package-data configuration regresses, the bundled JSON will
disappear from ``importlib.resources`` and these tests fail before a release
ships a wheel with missing constitutions.
"""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

from aafp_commons.constitutions import ConstitutionManifest
from aafp_commons.packages import default_registry


def _bundled_constitution_path(package_id: str, version: str) -> Path:
    """Resolve a bundled constitution JSON from the wheel, falling back to the
    source-tree root (mirroring ``aafp_commons.protocols.schema_path``)."""
    bundled = files("aafp_commons").joinpath("constitutions", package_id, f"{version}.json")
    if bundled.is_file():
        return Path(bundled)
    # Source checkout: constitutions/ lives at the repository root.
    return Path(__file__).resolve().parent.parent / "constitutions" / package_id / f"{version}.json"


def _bundled_manifest(package_id: str, version: str) -> ConstitutionManifest:
    path = _bundled_constitution_path(package_id, version)
    if not path.is_file():
        raise AssertionError(
            f"bundled constitution {package_id}@{version} is missing from the installed package"
        )
    return ConstitutionManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))


def test_bundled_grok_truth_seeking_json_is_present() -> None:
    manifest = _bundled_manifest("grok-truth-seeking", "1.0.0")
    assert manifest.constitution_id == "grok-truth-seeking"
    assert manifest.version == "1.0.0"


def test_bundled_grok_truth_seeking_digest_matches_programmatic_manifest() -> None:
    from aafp_commons.packages.grok_truth_seeking import GROK_TRUTH_SEEKING_MANIFEST

    bundled = _bundled_manifest("grok-truth-seeking", "1.0.0")
    assert bundled.manifest_digest == GROK_TRUTH_SEEKING_MANIFEST.manifest_digest


def test_every_registered_package_has_a_bundled_json_with_matching_digest() -> None:
    registry = default_registry()
    for package in registry.list():
        bundled = _bundled_manifest(package.package_id, package.version)
        assert bundled == package.manifest
        assert bundled.manifest_digest == package.manifest.manifest_digest
