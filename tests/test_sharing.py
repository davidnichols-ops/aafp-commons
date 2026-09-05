from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from aafp_commons.cli import main
from aafp_commons.packages import default_registry
from aafp_commons.repository import CommonsRepository
from aafp_commons.sharing import (
    SNAPSHOT_SCHEMA,
    export_public_snapshot,
    import_public_snapshot,
    load_public_snapshot,
    search_public_snapshot,
)


def test_export_public_snapshot_is_explicit_and_portable(tmp_path: Path) -> None:
    output = tmp_path / "public" / "snapshot.json"
    snapshot = export_public_snapshot(CommonsRepository(tmp_path / "node"), output)
    assert snapshot == {
        "schema": SNAPSHOT_SCHEMA,
        "packets": [],
        "constitutions": [],
        "count": 0,
    }
    assert json.loads(output.read_text(encoding="utf-8")) == snapshot
    assert load_public_snapshot(output) == snapshot
    assert search_public_snapshot(snapshot, "missing") == []


def test_import_public_snapshot_empty_is_safe(tmp_path: Path, identity: object) -> None:
    repository = CommonsRepository(tmp_path / "node")
    assert import_public_snapshot(repository, {
        "schema": SNAPSHOT_SCHEMA, "packets": [], "constitutions": [], "count": 0,
    }, identity) == 0


def test_import_rejects_bad_packet_before_installing_manifests(
    tmp_path: Path, identity: object
) -> None:
    repository = CommonsRepository(tmp_path / "node")
    manifest = default_registry().get("grok-truth-seeking").manifest.to_dict()
    snapshot = {"schema": SNAPSHOT_SCHEMA, "packets": [{"not": "a signed packet"}],
                "constitutions": [manifest], "count": 1}
    import pytest
    with pytest.raises((KeyError, ValueError, TypeError)):
        import_public_snapshot(repository, snapshot, identity)
    assert not (tmp_path / "node" / "constitutions").exists()


def test_import_rejects_bad_manifest_before_installing_anything(
    tmp_path: Path, identity: object
) -> None:
    repository = CommonsRepository(tmp_path / "node")
    valid = default_registry().get("grok-truth-seeking").manifest.to_dict()
    invalid = {"schema": "aafp.commons/constitution-manifest@1"}
    snapshot = {"schema": SNAPSHOT_SCHEMA, "packets": [],
                "constitutions": [valid, invalid], "count": 0}
    import pytest
    with pytest.raises((KeyError, ValueError, TypeError)):
        import_public_snapshot(repository, snapshot, identity)
    assert not (tmp_path / "node" / "constitutions").exists()


def test_cli_sharing_export_reports_artifact(tmp_path: Path, capsys: object) -> None:
    output = tmp_path / "snapshot.json"
    assert main(["sharing", "export", str(tmp_path / "node"), str(output)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["schema"] == SNAPSHOT_SCHEMA
    assert result["exported"] is True
    assert main(["sharing", "search", str(output), "anything"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["schema"] == "aafp.commons/research-search@1"
    assert result["results"] == []
    assert main(["sharing", "verify", str(output)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["verified"] is True
    index_path = tmp_path / "index.json"
    assert main(["sharing", "index", str(index_path), str(output)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["schema"] == "aafp.commons/research-index@1"
    assert result["count"] == 0
    assert main(["sharing", "stats", str(index_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["schema"] == "aafp.commons/research-stats@1"
    assert result["packet_count"] == 0
    schema = json.loads(
        (Path(__file__).parents[1] / "protocols" / "research-stats@1.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(result)


def test_cli_sharing_verify_returns_structured_error(tmp_path: Path, capsys: object) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema":"aafp.commons/research-snapshot@1","packets":[]}', encoding="utf-8")
    assert main(["sharing", "verify", str(bad)]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["schema"] == "aafp.commons/research-error@1"
