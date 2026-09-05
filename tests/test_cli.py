from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from aafp_commons.cli import main


def test_cli_constitutions_list_outputs_three_packages(capsys: object) -> None:
    exit_code = main(["constitutions", "list"])
    captured = _capture(capsys)
    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["schema"] == "aafp.commons/constitution-catalog@1"
    assert data["count"] == 3
    ids = {pkg["package_id"] for pkg in data["packages"]}
    assert ids == {"anthropic-cc0", "grok-truth-seeking", "gpt-astra-6"}


def test_cli_protocols_list_is_machine_readable(capsys: object) -> None:
    assert main(["protocols", "list"]) == 0
    data = json.loads(_capture(capsys).out)
    assert data["schema"] == "aafp.commons/protocol-catalog@1"
    assert data["count"] == len(data["protocols"])
    assert any(item["protocol_id"] == "agent-join@1" for item in data["protocols"])


def test_cli_protocols_show_returns_exact_schema(capsys: object) -> None:
    assert main(["protocols", "show", "agent-join@1"]) == 0
    data = json.loads(_capture(capsys).out)
    assert data["protocol_id"] == "agent-join@1"
    assert data["schema_document"]["$id"].endswith("agent-join@1")


def test_cli_protocols_show_raw_emits_schema_document(capsys: object) -> None:
    assert main(["protocols", "show", "agent-join@1", "--raw"]) == 0
    data = json.loads(_capture(capsys).out)
    assert data["$id"].endswith("agent-join@1")
    assert data["type"] == "object"


def test_cli_protocols_show_unknown_returns_error(capsys: object) -> None:
    assert main(["protocols", "show", "unknown@1"]) == 1
    data = json.loads(_capture(capsys).out)
    assert data["schema"] == "aafp.commons/protocol-error@1"
    assert "unknown@1" in data["error"]
    schema = json.loads(
        (Path(__file__).parents[1] / "protocols" / "protocol-error@1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(data)


def test_cli_constitutions_show_anthropic_cc0(capsys: object) -> None:
    exit_code = main(["constitutions", "show", "anthropic-cc0"])
    captured = _capture(capsys)
    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["schema"] == "aafp.commons/constitution-package@1"
    assert data["package_id"] == "anthropic-cc0"
    assert data["display_name"] == "Anthropic Constitution (CC0)"


def test_cli_constitutions_show_accepts_exact_version(capsys: object) -> None:
    assert main(["constitutions", "show", "anthropic-cc0@1.0.0"]) == 0
    data = json.loads(_capture(capsys).out)
    assert data["package_id"] == "anthropic-cc0"
    assert data["version"] == "1.0.0"
    assert "guidance" in data
    assert len(data["guidance"]["text"]) > 500
    assert "source" in data
    assert data["source"]["license"] == "CC0-1.0"


def test_cli_constitutions_show_unknown_package_returns_error(capsys: object) -> None:
    exit_code = main(["constitutions", "show", "nonexistent"])
    captured = _capture(capsys)
    assert exit_code == 1
    data = json.loads(captured.out)
    assert data["schema"] == "aafp.commons/constitution-package-error@1"
    assert "error" in data
    schema_path = (
        Path(__file__).parents[1] / "protocols" / "constitution-package-error@1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(data)


def test_cli_constitutions_show_unknown_exact_version_returns_error(capsys: object) -> None:
    assert main(["constitutions", "show", "anthropic-cc0@9.9.9"]) == 1
    data = json.loads(_capture(capsys).out)
    assert data["schema"] == "aafp.commons/constitution-package-error@1"
    assert "9.9.9" in data["error"]


def test_cli_constitutions_install_creates_manifest_file(
    tmp_path: Path, capsys: object
) -> None:
    exit_code = main(["constitutions", "install", "anthropic-cc0", str(tmp_path)])
    captured = _capture(capsys)
    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["installed"] is True
    assert data["constitution_id"] == "anthropic-cc0"
    manifest_path = tmp_path / "constitutions" / "anthropic-cc0" / "1.0.0.json"
    assert manifest_path.exists()
    stored = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert stored["constitution_id"] == "anthropic-cc0"
    assert "guidance" in stored
    assert "source" in stored


def test_cli_constitutions_install_unknown_package_returns_error(
    tmp_path: Path, capsys: object
) -> None:
    exit_code = main(["constitutions", "install", "nonexistent", str(tmp_path)])
    captured = _capture(capsys)
    assert exit_code == 1
    data = json.loads(captured.out)
    assert "error" in data


def test_cli_constitutions_import_validates_and_installs_manifest(
    tmp_path: Path, capsys: object
) -> None:
    source = tmp_path / "source"
    main(["constitutions", "install", "gpt-astra-6", str(source)])
    output = json.loads(_capture(capsys).out)
    assert output["schema"] == "aafp.commons/constitution-installation@1"
    manifest = source / "constitutions" / "gpt-astra-6" / "1.0.0.json"
    target = tmp_path / "target"
    exit_code = main(["constitutions", "import", str(manifest), str(target)])
    data = json.loads(_capture(capsys).out)
    assert exit_code == 0
    assert data["imported"] is True
    assert data["digest"] == output["digest"]
    assert (target / "constitutions" / "gpt-astra-6" / "1.0.0.json").exists()


def test_cli_constitutions_import_rejects_mutated_existing_version(
    tmp_path: Path, capsys: object
) -> None:
    source = tmp_path / "source"
    main(["constitutions", "install", "gpt-astra-6", str(source)])
    _capture(capsys)
    manifest = source / "constitutions" / "gpt-astra-6" / "1.0.0.json"
    value = json.loads(manifest.read_text(encoding="utf-8"))
    value["description"] = "tampered"
    mutated = tmp_path / "mutated.json"
    mutated.write_text(json.dumps(value), encoding="utf-8")
    exit_code = main(["constitutions", "import", str(mutated), str(source)])
    data = json.loads(_capture(capsys).out)
    assert exit_code == 1
    assert data["imported"] is False
    assert "different content" in data["error"]


def test_cli_constitutions_export_writes_exact_manifest(tmp_path: Path, capsys: object) -> None:
    root = tmp_path / "root"
    main(["constitutions", "install", "anthropic-cc0", str(root)])
    _capture(capsys)
    output = tmp_path / "exported.json"
    exit_code = main([
        "constitutions", "export", "anthropic-cc0@1.0.0", str(root), str(output)
    ])
    data = json.loads(_capture(capsys).out)
    assert exit_code == 0
    assert data["exported"] is True
    exported = json.loads(output.read_text(encoding="utf-8"))
    assert exported["constitution_id"] == "anthropic-cc0"
    assert data["digest"].startswith("sha256:")


def test_cli_constitutions_import_dir_onboards_bundle(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "source"
    bundle = tmp_path / "bundle"
    target = tmp_path / "target"
    for package_id in ("grok-truth-seeking", "gpt-astra-6"):
        main(["constitutions", "install", package_id, str(source)])
        _capture(capsys)
        output = bundle / f"{package_id}.json"
        main(["constitutions", "export", f"{package_id}@1.0.0", str(source), str(output)])
        _capture(capsys)
    (bundle / "duplicate.json").write_text(
        (bundle / "gpt-astra-6.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    exit_code = main(["constitutions", "import-dir", str(bundle), str(target)])
    data = json.loads(_capture(capsys).out)
    assert exit_code == 0
    assert data["count"] == 2
    assert len(list((target / "constitutions").iterdir())) == 2


def test_cli_constitutions_import_dir_preflights_conflicts(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "source"
    bundle = tmp_path / "bundle"
    target = tmp_path / "target"
    main(["constitutions", "install", "grok-truth-seeking", str(source)])
    _capture(capsys)
    main(["constitutions", "install", "gpt-astra-6", str(source)])
    _capture(capsys)
    target.mkdir()
    main(["constitutions", "install", "grok-truth-seeking", str(target)])
    _capture(capsys)
    for package_id in ("gpt-astra-6", "grok-truth-seeking"):
        main(["constitutions", "export", f"{package_id}@1.0.0", str(source),
              str(bundle / f"{package_id}.json")])
        _capture(capsys)
    mutated = bundle / "grok-truth-seeking.json"
    value = json.loads(mutated.read_text(encoding="utf-8"))
    value["description"] = "conflict"
    mutated.write_text(json.dumps(value), encoding="utf-8")
    exit_code = main(["constitutions", "import-dir", str(bundle), str(target)])
    data = json.loads(_capture(capsys).out)
    assert exit_code == 1
    assert data["imported"] is False
    assert not (target / "constitutions" / "gpt-astra-6").exists()


# --- catalog commands ---


def test_cli_catalog_list_empty_repository(tmp_path: Path, capsys: object) -> None:
    exit_code = main(["catalog", "list", str(tmp_path)])
    captured = _capture(capsys)
    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["count"] == 0
    assert data["constitutions"] == []


def test_cli_catalog_list_after_install(tmp_path: Path, capsys: object) -> None:
    # Install a built-in package first.
    main(["constitutions", "install", "anthropic-cc0", str(tmp_path)])
    _capture(capsys)  # drain prior output

    exit_code = main(["catalog", "list", str(tmp_path)])
    captured = _capture(capsys)
    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["count"] == 1
    assert data["constitutions"][0]["constitution_id"] == "anthropic-cc0"
    assert data["constitutions"][0]["has_guidance"] is True


def test_cli_catalog_select_no_match(tmp_path: Path, capsys: object) -> None:
    exit_code = main(["catalog", "select", str(tmp_path), "--runtime", "claude"])
    captured = _capture(capsys)
    assert exit_code == 1
    data = json.loads(captured.out)
    assert data["selected"] is None


def test_cli_catalog_select_by_runtime(tmp_path: Path, capsys: object) -> None:
    from aafp_commons.constitutions import (
        ConstitutionManifest,
        RuntimeCompatibility,
    )
    from aafp_commons.repository import CommonsRepository

    CommonsRepository(tmp_path).install_constitution(
        ConstitutionManifest(
            constitution_id="claude-safe",
            version="1.0",
            namespace_prefixes=("commons/claude",),
            runtime_compatibility=RuntimeCompatibility(compatible=("claude",)),
        )
    )

    exit_code = main(["catalog", "select", str(tmp_path), "--runtime", "claude"])
    captured = _capture(capsys)
    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["selected"] is True
    assert data["constitution_ref"]["constitution_id"] == "claude-safe"


def test_cli_catalog_select_require_guidance(tmp_path: Path, capsys: object) -> None:
    main(["constitutions", "install", "anthropic-cc0", str(tmp_path)])
    _capture(capsys)

    exit_code = main([
        "catalog", "select", str(tmp_path), "--require-guidance",
    ])
    captured = _capture(capsys)
    assert exit_code == 0
    data = json.loads(captured.out)
    assert data["constitution_ref"]["constitution_id"] == "anthropic-cc0"
    assert "full constitution" in data["guidance"]["text"].lower()
    assert data["provider_constraint_policy"] == "preserve"


def test_cli_agent_ask_emits_machine_readable_request(
    tmp_path: Path, capsys: object
) -> None:
    from aafp_commons.identity import derive_agent_id

    main(["constitutions", "install", "grok-truth-seeking", str(tmp_path)])
    _capture(capsys)
    agent_id = derive_agent_id(b"grok-agent")
    exit_code = main([
        "agent", "ask", str(tmp_path),
        "--agent-id", agent_id,
        "--runtime", "grok",
        "--namespace", "commons/frontend/react",
        "--kind", "finding",
        "--purpose", "Work under explicit truth-seeking guidance.",
    ])
    data = json.loads(_capture(capsys).out)
    assert exit_code == 0
    assert data["schema"] == "aafp.commons/constitution-adoption-request@1"
    assert data["requested"] is True
    assert data["requester_agent_id"] == agent_id
    assert data["constitution"]["constitution_id"] == "grok-truth-seeking"
    assert data["constitution"]["digest"].startswith("sha256:")
    assert data["request_id"].startswith("sha256:")
    assert data["status"] == "awaiting-runtime-acceptance"
    assert data["provider_constraint_policy"] == "preserve"
    assert len(data["guidance"]["text"]) > 500
    assert "grants no capability" in data["acceptance_effect"]
    request_path = tmp_path / "adoption-requests" / (
        data["request_id"].removeprefix("sha256:") + ".json"
    )
    assert request_path.exists()

    exit_code = main(["agent", "requests", str(tmp_path)])
    listed = json.loads(_capture(capsys).out)
    assert exit_code == 0
    assert listed["count"] == 1
    assert listed["requests"][0]["request_id"] == data["request_id"]


def test_cli_agent_join_failure_keeps_handshake_but_no_request(
    tmp_path: Path, capsys: object
) -> None:
    from aafp_commons.identity import derive_agent_id
    from aafp_commons.repository import CommonsRepository

    exit_code = main([
        "agent", "join", str(tmp_path),
        "--agent-id", derive_agent_id(b"failed-join-agent"),
        "--runtime", "grok", "--runtime-version", "3",
        "--identity-convention", "runtime-native", "--identity-hint", "probe",
        "--namespace", "commons/research", "--kind", "finding",
    ])
    data = json.loads(_capture(capsys).out)
    assert exit_code == 1
    assert data["joined"] is False
    repository = CommonsRepository(tmp_path)
    assert repository.runtime_handshakes.list()
    assert repository.adoption_requests.list() == []


def test_cli_agent_join_composes_handshake_and_request(tmp_path: Path, capsys: object) -> None:
    from aafp_commons.identity import derive_agent_id

    main(["constitutions", "install", "grok-truth-seeking", str(tmp_path)])
    _capture(capsys)
    exit_code = main([
        "agent", "join", str(tmp_path),
        "--agent-id", derive_agent_id(b"join-cli-agent"),
        "--runtime", "grok", "--runtime-version", "3",
        "--identity-convention", "runtime-native", "--identity-hint", "session",
        "--namespace", "commons/research", "--kind", "finding",
        "--constitution", "grok-truth-seeking@1.0.0",
    ])
    data = json.loads(_capture(capsys).out)
    assert exit_code == 0
    assert data["schema"] == "aafp.commons/agent-join@1"
    assert data["joined"] is True
    assert data["state"] == "awaiting-runtime-acceptance"
    assert data["handshake_id"].startswith("sha256:")
    assert data["request_id"].startswith("sha256:")
    assert data["next_action"]["request_id"] == data["request_id"]
    assert data["next_action"]["handshake_id"] == data["handshake_id"]
    assert data["next_action"]["accept_command"].endswith("--accept")
    assert data["next_action"]["request_id"] in data["next_action"]["context_command"]


def test_cli_agent_join_honors_accepted_constitution_preference(
    tmp_path: Path, capsys: object
) -> None:
    from aafp_commons.identity import derive_agent_id

    main(["constitutions", "install-all", str(tmp_path)])
    _capture(capsys)
    exit_code = main([
        "agent", "join", str(tmp_path),
        "--agent-id", derive_agent_id(b"preference-cli-agent"),
        "--runtime", "codex", "--runtime-version", "1",
        "--identity-convention", "runtime-native", "--identity-hint", "session",
        "--namespace", "commons/research", "--kind", "finding",
        "--accepted-constitution", "gpt-astra-6@1.0.0",
    ])
    output = json.loads(_capture(capsys).out)
    assert exit_code == 0
    assert output["constitution"]["constitution_id"] == "gpt-astra-6"


def test_cli_constitution_search_is_machine_readable(capsys: object) -> None:
    assert main(["constitutions", "search", "anti-sycophancy"]) == 0
    output = json.loads(_capture(capsys).out)
    assert output["schema"] == "aafp.commons/constitution-catalog@1"
    assert [item["package_id"] for item in output["packages"]] == [
        "grok-truth-seeking"
    ]
    assert main(["constitutions", "search", "corrigibility"]) == 0
    guidance_search = json.loads(_capture(capsys).out)
    assert [item["package_id"] for item in guidance_search["packages"]] == [
        "anthropic-cc0"
    ]


def test_cli_constitution_install_all_installs_every_builtin(
    tmp_path: Path, capsys: object
) -> None:
    assert main(["constitutions", "install-all", str(tmp_path)]) == 0
    output = json.loads(_capture(capsys).out)
    assert output["schema"] == "aafp.commons/constitution-installation@1"
    assert output["installed"] is True
    assert output["count"] == 3
    assert main(["constitutions", "install-all", str(tmp_path)]) == 0
    repeated = json.loads(_capture(capsys).out)
    assert repeated["constitutions"] == output["constitutions"]
    assert main(["constitutions", "verify", str(tmp_path)]) == 0
    assert json.loads(_capture(capsys).out)["count"] == 3


def test_cli_outputs_validate_against_published_schemas(
    tmp_path: Path, capsys: object
) -> None:
    schema_root = Path(__file__).parents[1] / "protocols"

    def validate(schema_name: str, value: dict[str, object]) -> None:
        schema = json.loads((schema_root / schema_name).read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(value)

    assert main(["constitutions", "install-all", str(tmp_path)]) == 0
    validate(
        "constitution-installation@1.schema.json",
        json.loads(_capture(capsys).out),
    )
    assert main(["constitutions", "search", "corrigibility"]) == 0
    validate("constitution-catalog@1.schema.json", json.loads(_capture(capsys).out))
    assert main(["constitutions", "show", "anthropic-cc0@1.0.0"]) == 0
    validate("constitution-package@1.schema.json", json.loads(_capture(capsys).out))
    assert main([
        "agent", "join", str(tmp_path),
        "--agent-id", "aafp:" + "0" * 64,
        "--runtime", "grok", "--runtime-version", "3",
        "--identity-convention", "runtime-native", "--identity-hint", "session",
        "--namespace", "commons/research", "--kind", "finding",
        "--constitution", "grok-truth-seeking@1.0.0",
    ]) == 0
    validate("agent-join@1.schema.json", json.loads(_capture(capsys).out))
    assert main(["protocols", "list"]) == 0
    validate("protocol-catalog@1.schema.json", json.loads(_capture(capsys).out))
    assert main(["protocols", "show", "agent-join@1"]) == 0
    validate("protocol-show@1.schema.json", json.loads(_capture(capsys).out))
    assert main(["agent", "requests", str(tmp_path)]) == 0
    validate(
        "constitution-adoption-request-list@1.schema.json",
        json.loads(_capture(capsys).out),
    )
    assert main(["runtime", "handshakes", str(tmp_path)]) == 0
    validate("runtime-handshake-list@1.schema.json", json.loads(_capture(capsys).out))


def test_cli_constitution_install_all_preflights_conflicts(
    tmp_path: Path, capsys: object
) -> None:
    main(["constitutions", "install", "grok-truth-seeking", str(tmp_path)])
    _capture(capsys)
    path = tmp_path / "constitutions" / "grok-truth-seeking" / "1.0.0.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["description"] = "conflicting content"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert main(["constitutions", "install-all", str(tmp_path)]) == 1
    output = json.loads(_capture(capsys).out)
    assert output["installed"] is False
    assert not (tmp_path / "constitutions" / "anthropic-cc0").exists()


def test_cli_constitution_verify_reports_content_addresses(
    tmp_path: Path, capsys: object
) -> None:
    main(["constitutions", "install", "anthropic-cc0", str(tmp_path)])
    _capture(capsys)
    assert main(["constitutions", "verify", str(tmp_path)]) == 0
    output = json.loads(_capture(capsys).out)
    assert output["valid"] is True
    assert output["count"] == 1
    assert output["constitutions"][0]["digest"].startswith("sha256:")

    manifest_path = tmp_path / "constitutions" / "anthropic-cc0" / "1.0.0.json"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace(
            '"schema": "aafp.commons/constitution-manifest@1"',
            '"schema": "tampered"',
            1,
        ),
        encoding="utf-8",
    )
    assert main(["constitutions", "verify", str(tmp_path)]) == 1
    invalid = json.loads(_capture(capsys).out)
    assert invalid["valid"] is False
    assert "error" in invalid


def test_cli_agent_ask_rejects_invalid_identity(
    tmp_path: Path, capsys: object
) -> None:
    main(["constitutions", "install", "gpt-astra-6", str(tmp_path)])
    _capture(capsys)
    exit_code = main([
        "agent", "ask", str(tmp_path),
        "--agent-id", "not-an-aafp-id",
        "--runtime", "codex",
        "--namespace", "commons/research",
        "--kind", "finding",
    ])
    data = json.loads(_capture(capsys).out)
    assert exit_code == 1
    assert data["requested"] is False
    assert "agent_id" in data["error"]


def test_cli_agent_accepts_and_emits_working_context(
    tmp_path: Path, capsys: object
) -> None:
    from aafp_commons.identity import derive_agent_id

    main(["constitutions", "install", "gpt-astra-6", str(tmp_path)])
    _capture(capsys)
    main([
        "runtime", "handshake", str(tmp_path),
        "--runtime", "codex", "--runtime-version", "1",
        "--identity-convention", "runtime-native", "--identity-hint", "session",
    ])
    handshake = json.loads(_capture(capsys).out)
    main([
        "agent", "ask", str(tmp_path),
        "--agent-id", derive_agent_id(b"astra-agent"),
        "--runtime", "codex",
        "--namespace", "commons/frontend/react",
        "--kind", "finding",
    ])
    request = json.loads(_capture(capsys).out)

    exit_code = main([
        "agent", "respond", str(tmp_path), request["request_id"], "--accept",
    ])
    decision = json.loads(_capture(capsys).out)
    assert exit_code == 0
    assert decision["status"] == "accepted"
    assert decision["recorded"] is True
    assert decision["decision_id"].startswith("sha256:")
    assert "grants no identity" in decision["effect"]

    exit_code = main([
        "agent", "context", str(tmp_path), request["request_id"],
    ])
    context = json.loads(_capture(capsys).out)
    assert exit_code == 0
    assert context["active"] is True
    assert context["request_id"] == request["request_id"]
    assert context["decision_id"] == decision["decision_id"]
    assert context["constitution"]["constitution_id"] == "gpt-astra-6"
    assert len(context["guidance"]["text"]) > 500
    assert context["provider_constraint_policy"] == "preserve"
    exit_code = main([
        "agent", "context", str(tmp_path), request["request_id"],
        "--handshake-id", handshake["handshake_id"],
    ])
    linked_context = json.loads(_capture(capsys).out)
    assert exit_code == 0
    assert linked_context["handshake_id"] == handshake["handshake_id"]
    assert not (tmp_path / "ledger.jsonl").exists()


def test_cli_context_rejects_handshake_from_different_runtime(
    tmp_path: Path, capsys: object
) -> None:
    from aafp_commons.identity import derive_agent_id

    main(["constitutions", "install", "gpt-astra-6", str(tmp_path)])
    _capture(capsys)
    main([
        "runtime", "handshake", str(tmp_path),
        "--runtime", "grok", "--runtime-version", "3",
        "--identity-convention", "runtime-native", "--identity-hint", "session",
    ])
    handshake = json.loads(_capture(capsys).out)
    main([
        "agent", "ask", str(tmp_path),
        "--agent-id", derive_agent_id(b"mismatch-agent"),
        "--runtime", "codex", "--namespace", "commons/research", "--kind", "finding",
    ])
    request = json.loads(_capture(capsys).out)
    main(["agent", "respond", str(tmp_path), request["request_id"], "--accept"])
    _capture(capsys)
    exit_code = main([
        "agent", "context", str(tmp_path), request["request_id"],
        "--handshake-id", handshake["handshake_id"],
    ])
    output = json.loads(_capture(capsys).out)
    assert exit_code == 1
    assert output["active"] is False
    assert "runtime" in output["error"]


def test_cli_rejected_request_has_no_working_context(
    tmp_path: Path, capsys: object
) -> None:
    from aafp_commons.identity import derive_agent_id

    main(["constitutions", "install", "anthropic-cc0", str(tmp_path)])
    _capture(capsys)
    main([
        "agent", "ask", str(tmp_path),
        "--agent-id", derive_agent_id(b"claude-agent"),
        "--runtime", "claude",
        "--namespace", "commons/research",
        "--kind", "finding",
    ])
    request = json.loads(_capture(capsys).out)
    assert main([
        "agent", "respond", str(tmp_path), request["request_id"],
        "--reject", "--reason", "Local runtime policy declined it.",
    ]) == 0
    _capture(capsys)
    assert main([
        "agent", "context", str(tmp_path), request["request_id"],
    ]) == 1
    context = json.loads(_capture(capsys).out)
    assert context["active"] is False
    assert "rejected" in context["error"]


def _capture(capsys: object) -> object:
    """Extract captured stdout from pytest's capsys fixture."""
    return capsys.readouterr()  # type: ignore[attr-defined]
