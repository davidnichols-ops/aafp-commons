from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

WORLD_FIELDS = {
    "packet_set_merkle",
    "local_tip",
    "peer_tips",
    "fork_ids",
    "conflict_ids",
    "resolution_ids",
    "packet_count",
    "posture",
    "agent_id",
    "constitution",
    "review_queue",
}


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _init(home: Path) -> None:
    environment = os.environ.copy()
    environment["COMMONS_HOME"] = str(home)
    result = subprocess.run(
        [sys.executable, "-m", "aafp_commons.w1", "init"],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert _json_output(result.stdout)["posture"] == "subject"


def _propose(home: Path) -> str:
    environment = os.environ.copy()
    environment["COMMONS_HOME"] = str(home)
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "commons_propose",
            "arguments": {
                "namespace": "commons/w3",
                "claim": "The W3 loopback pull preserves packet-set identity.",
                "evidence": [{"kind": "test", "uri": "artifact://w3/loopback"}],
                "confidence": 0.9,
            },
        },
    }
    result = subprocess.run(
        [sys.executable, "-m", "aafp_commons.w1", "mcp"],
        check=True,
        capture_output=True,
        text=True,
        input=json.dumps(request) + "\n",
        env=environment,
    )
    response = _json_output(result.stdout)
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is False
    return str(structured["packet_id"])


def _wait_for_world(port: int) -> dict[str, object]:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/world", timeout=0.25) as response:
                return json.load(response)
        except (OSError, ValueError):
            time.sleep(0.05)
    raise AssertionError(f"server did not become ready on port {port}")


def _start(home: Path, port: int) -> subprocess.Popen[str]:
    environment = os.environ.copy()
    environment["COMMONS_HOME"] = str(home)
    return subprocess.Popen(
        [sys.executable, "-m", "aafp_commons.w1", "serve", "--port", str(port)],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_two_process_http_pull_preserves_packet_set_merkle(tmp_path: Path) -> None:
    home_a = tmp_path / "node-a"
    home_b = tmp_path / "node-b"
    _init(home_a)
    _init(home_b)
    packet_id = _propose(home_a)

    port_a, port_b = _free_port(), _free_port()
    processes = [_start(home_a, port_a), _start(home_b, port_b)]
    try:
        world_a_before = _wait_for_world(port_a)
        world_b_before = _wait_for_world(port_b)
        assert set(world_a_before) == WORLD_FIELDS
        assert set(world_b_before) == WORLD_FIELDS
        assert world_a_before["packet_count"] == 1
        assert world_b_before["packet_count"] == 0

        request = Request(
            f"http://127.0.0.1:{port_b}/replicate",
            data=json.dumps({"peer": f"http://127.0.0.1:{port_a}"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            replication = json.load(response)
        assert replication == {"accepted": 1, "already_present": 0, "ok": True, "packet_count": 1}

        world_a_after = _wait_for_world(port_a)
        world_b_after = _wait_for_world(port_b)
        assert packet_id in _packet_ids(home_a)
        assert set(world_b_after) == WORLD_FIELDS
        assert world_a_after["packet_set_merkle"] == world_b_after["packet_set_merkle"]
        assert world_b_after["packet_count"] == 1
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            process.wait(timeout=5)


def _packet_ids(home: Path) -> set[str]:
    return {f"sha256:{path.stem}" for path in (home / "objects").glob("*.json")}


def _json_output(output: str) -> dict[str, object]:
    start = output.find("{")
    assert start >= 0
    return json.loads(output[start:])
