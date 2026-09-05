from __future__ import annotations

import json
from pathlib import Path

import pytest

from aafp_commons import (
    CommonsRepository,
    ConstitutionRef,
    FileHandshakeStore,
    RuntimeHandshake,
    default_registry,
)
from aafp_commons.discovery import ConstitutionCatalog


def _manifest_ref(package_id: str) -> ConstitutionRef:
    return default_registry().get(package_id).manifest.ref


def test_handshake_is_content_addressed_and_round_trips(tmp_path: Path) -> None:
    handshake = RuntimeHandshake(
        runtime="grok",
        runtime_version="grok-3",
        identity_convention="aafp-sha256-pubkey",
        identity_hint="derive from a runtime session public key",
        accepted_constitutions=(_manifest_ref("grok-truth-seeking"),),
        declared_at=123,
    )
    store = FileHandshakeStore(tmp_path)
    assert store.record(handshake) == handshake.handshake_id
    assert store.record(handshake) == handshake.handshake_id
    assert store.get(handshake.handshake_id) == handshake
    assert store.by_runtime("grok") == [handshake]


def test_handshake_rejects_unpinned_or_unknown_constitution() -> None:
    with pytest.raises(ValueError, match="exact sha256"):
        RuntimeHandshake(
            runtime="grok",
            runtime_version="3",
            identity_convention="runtime-native",
            identity_hint="",
            accepted_constitutions=(ConstitutionRef("grok", "1.0.0"),),
        )
    with pytest.raises(ValueError, match="identity_convention"):
        RuntimeHandshake(
            runtime="grok",
            runtime_version="3",
            identity_convention="trusted-provider-key",
            identity_hint="",
        )


def test_handshake_store_rejects_tampering(tmp_path: Path) -> None:
    handshake = RuntimeHandshake(
        runtime="claude",
        runtime_version="4",
        identity_convention="unspecified",
        identity_hint="",
        declared_at=1,
    )
    store = FileHandshakeStore(tmp_path)
    store.record(handshake)
    path = store.handshake_path(handshake.handshake_id)
    content = path.read_text(encoding="utf-8").replace(
        '"runtime_version": "4"', '"runtime_version": "5"'
    )
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="content address"):
        store.get(handshake.handshake_id)


def test_handshake_does_not_create_ledger_or_objects(tmp_path: Path) -> None:
    repository = CommonsRepository(tmp_path)
    handshake = RuntimeHandshake(
        runtime="codex",
        runtime_version="1",
        identity_convention="runtime-native",
        identity_hint="session identity is runtime-managed",
        declared_at=1,
    )
    repository.record_runtime_handshake(handshake)
    assert not (tmp_path / "ledger.jsonl").exists()
    assert not (tmp_path / "objects").exists()


def test_catalog_handshake_prefers_runtime_accepted_constitution(tmp_path: Path) -> None:
    repository = CommonsRepository(tmp_path)
    packages = default_registry().list()
    for package in packages:
        repository.install_constitution(package.manifest)
    handshake = RuntimeHandshake(
        runtime="grok",
        runtime_version="3",
        identity_convention="unspecified",
        identity_hint="",
        accepted_constitutions=(_manifest_ref("grok-truth-seeking"),),
        declared_at=1,
    )
    selected = ConstitutionCatalog(repository.constitutions).select_for_handshake(
        handshake, "commons/frontend/react", "finding"
    )
    assert selected is not None
    assert selected.constitution_id == "grok-truth-seeking"


def test_handshake_cli_emits_and_lists_record(tmp_path: Path, capsys: object) -> None:
    from aafp_commons.cli import main

    main(["constitutions", "install", "grok-truth-seeking", str(tmp_path)])
    capsys.readouterr()
    assert main([
        "runtime", "handshake", str(tmp_path),
        "--runtime", "grok", "--runtime-version", "3",
        "--identity-convention", "aafp-sha256-pubkey",
        "--identity-hint", "session public key",
        "--accepted-constitution", "grok-truth-seeking@1.0.0",
    ]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["recorded"] is True
    assert output["handshake_id"].startswith("sha256:")
    assert "does not prove AAFP identity" in output["boundary"]
    assert main(["runtime", "handshakes", str(tmp_path)]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["count"] == 1
    assert listed["handshakes"][0]["handshake_id"] == output["handshake_id"]
