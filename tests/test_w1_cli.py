from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from ironclad.trust import Identity

from aafp_commons.identity import derive_agent_id
from aafp_commons.models import EvidenceRef, KnowledgePacket, MethodRef
from aafp_commons.packages import default_registry
from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import sign_packet
from aafp_commons.w1 import main, world


def _run_world(home: Path) -> dict[str, object]:
    environment = os.environ.copy()
    environment["COMMONS_HOME"] = str(home)
    result = subprocess.run(
        [sys.executable, "-m", "aafp_commons.w1", "world"],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return json.loads(result.stdout)


def _wait_for_world(port: int) -> dict[str, object]:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/world", timeout=0.25) as response:
                return json.load(response)
        except (OSError, ValueError):
            time.sleep(0.05)
    raise AssertionError(f"server did not become ready on port {port}")


def _submit_one(root: Path, signer: Identity, authority: Identity) -> str:
    repository = CommonsRepository(root)
    repository.initialize()
    constitution = default_registry().get("grok-truth-seeking", "1.0.0").manifest
    reference = repository.install_constitution(constitution)
    packet = KnowledgePacket(
        kind="finding",
        namespace="commons/w1",
        claim="The W1 local world preserves packet-set identity across nodes.",
        scope={"component": "w1"},
        evidence=(EvidenceRef(kind="test", uri="artifact://w1/two-node"),),
        confidence=0.9,
        author_agent_id=derive_agent_id(b"w1-test-agent"),
        constitution=reference,
        method=MethodRef("w1-two-node", "1.0"),
    )
    decision = repository.submit(sign_packet(packet, signer), authority)
    assert decision.accepted
    return packet.packet_id


def test_source_posture_and_init(monkeypatch, tmp_path: Path, capsys) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("COMMONS_HOME", str(home))

    assert main([]) == 0
    assert "posture=source" in capsys.readouterr().out

    assert main(["init"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["posture"] == "subject"
    assert (home / "identity.json").exists()
    assert (home / "constitutions" / "grok-truth-seeking" / "1.0.0.json").exists()
    assert world(home)["agent_id"] == result["agent_id"]


def test_world_schema_and_get(monkeypatch, tmp_path: Path, capsys) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("COMMONS_HOME", str(home))
    assert main(["init"]) == 0
    capsys.readouterr()
    packet_id = _submit_one(home, Identity.generate(), Identity.generate())
    output = world(home)
    assert set(output) == {
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
    }
    assert main(["get", packet_id]) == 0
    assert json.loads(capsys.readouterr().out)["packet"]["namespace"] == "commons/w1"


def test_two_process_worlds_share_packet_set_merkle(tmp_path: Path) -> None:
    home_a = tmp_path / "a"
    home_b = tmp_path / "b"
    signer = Identity.generate()
    _submit_one(home_a, signer, Identity.generate())
    _submit_one(home_b, signer, Identity.generate())
    assert world(home_a)["packet_set_merkle"] == world(home_b)["packet_set_merkle"]

    port_a, port_b = _free_port(), _free_port()
    processes = []
    try:
        for home, port in ((home_a, port_a), (home_b, port_b)):
            environment = os.environ.copy()
            environment["COMMONS_HOME"] = str(home)
            processes.append(
                subprocess.Popen(
                    [sys.executable, "-m", "aafp_commons.w1", "serve", "--port", str(port)],
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            )
        remote_a = _wait_for_world(port_a)
        remote_b = _wait_for_world(port_b)
        assert remote_a["packet_set_merkle"] == remote_b["packet_set_merkle"]
        assert remote_a["packet_count"] == 1
        assert remote_b["packet_count"] == 1
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            process.wait(timeout=5)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
