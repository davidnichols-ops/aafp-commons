from __future__ import annotations

import io
import json
from pathlib import Path

from aafp_commons.mcp_stdio import serve_stdio
from aafp_commons.w1 import main


def _exchange(requests: list[dict[str, object]], home: Path) -> list[dict[str, object]]:
    incoming = io.BytesIO("\n".join(json.dumps(item) for item in requests).encode() + b"\n")
    outgoing = io.BytesIO()
    assert serve_stdio(incoming, outgoing, home) == 0
    return [json.loads(line) for line in outgoing.getvalue().splitlines()]


def _call(
    name: str,
    arguments: dict[str, object] | None = None,
    request_id: int = 1,
) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    }


def test_initialize_and_tools_list_are_frozen(tmp_path: Path) -> None:
    responses = _exchange(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ],
        tmp_path / "source",
    )
    assert responses[0]["result"]["serverInfo"]["name"] == "commons"
    tools = responses[1]["result"]["tools"]
    assert [tool["name"] for tool in tools] == [
        "commons_world",
        "commons_query",
        "commons_get",
        "commons_assume_constitution",
        "commons_propose",
        "commons_conflicts",
        "commons_resolutions",
    ]
    descriptions = " ".join(tool["description"] for tool in tools).lower()
    assert "evidence" in descriptions
    assert "constitution" in descriptions


def test_source_posture_returns_machine_readable_errors(tmp_path: Path) -> None:
    responses = _exchange(
        [
            _call("commons_assume_constitution", request_id=1),
            _call(
                "commons_propose",
                {
                    "namespace": "commons/mcp",
                    "claim": "Source posture must not write packets.",
                    "evidence": [{"kind": "test", "uri": "artifact://source"}],
                },
                request_id=2,
            ),
        ],
        tmp_path / "source",
    )
    assert responses[0]["result"]["isError"] is True
    assert responses[0]["result"]["structuredContent"]["error"]["code"] == "INIT_REQUIRED"
    assert responses[1]["result"]["structuredContent"]["error"]["code"] == "SOURCE_POSTURE"
    assert not (tmp_path / "source").exists()


def test_initialized_subject_can_propose_and_get(tmp_path: Path, monkeypatch, capsys) -> None:
    home = tmp_path / "subject"
    monkeypatch.setenv("COMMONS_HOME", str(home))
    assert main(["init"]) == 0
    capsys.readouterr()
    responses = _exchange(
        [
            _call(
                "commons_propose",
                {
                    "namespace": "commons/mcp",
                    "claim": "An evidence-backed MCP proposal is admitted locally.",
                    "evidence": [{"kind": "test", "uri": "artifact://mcp"}],
                    "confidence": 0.9,
                },
                request_id=1,
            ),
        ],
        home,
    )
    result = responses[0]["result"]
    assert result["isError"] is False
    packet_id = result["structuredContent"]["packet_id"]
    get_response = _exchange(
        [_call("commons_get", {"packet_id": packet_id}, request_id=2)], home
    )[0]
    assert (
        get_response["result"]["structuredContent"]["packet"]["packet"]["namespace"]
        == "commons/mcp"
    )
