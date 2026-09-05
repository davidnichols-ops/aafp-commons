"""W9 local three-subject simulation harness.

Boots three independent Commons subjects (A, B, C) against isolated
``COMMONS_HOME`` directories under ``/tmp/commons-sim-*``, drives them through
the existing W1 CLI and W2 MCP surfaces, prints their ``/world`` objects, and
stops cleanly while leaving every ledger intact.

Run from the project root:

    uv run --no-sync python scripts/sim_agents.py

The harness uses only existing surfaces (``commons init``, ``commons mcp``
``commons_propose``, ``commons serve`` ``/world`` and ``/replicate``). It
introduces no new CLI subcommands, no new MCP tool names, no transport, and no
packaging. Packet namespaces stay under ``commons/sim/ml/``.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

HOMES: tuple[str, str, str] = (
    "/tmp/commons-sim-A",
    "/tmp/commons-sim-B",
    "/tmp/commons-sim-C",
)
SUBJECTS: tuple[str, str, str] = ("A", "B", "C")
PROPOSE_NAMESPACE = "commons/sim/ml/observation"
WORLD_FIELDS: frozenset[str] = frozenset(
    {
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
)


@dataclass(frozen=True)
class Subject:
    label: str
    home: str
    port: int


def _env_for(home: str) -> dict[str, str]:
    environment = os.environ.copy()
    environment["COMMONS_HOME"] = home
    return environment


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _reset_homes() -> None:
    for home in HOMES:
        path = Path(home)
        if path.exists():
            shutil.rmtree(path)


def _init_subject(label: str, home: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, "-m", "aafp_commons.w1", "init"],
        check=True,
        capture_output=True,
        text=True,
        env=_env_for(home),
    )
    payload = _json_from_output(result.stdout)
    if payload.get("posture") != "subject":
        raise RuntimeError(f"subject {label} did not reach subject posture: {payload}")
    print(f"[{label}] init home={home} agent_id={payload.get('agent_id')}")
    return payload


def _propose_via_mcp(label: str, home: str) -> str:
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "commons_propose",
            "arguments": {
                "namespace": PROPOSE_NAMESPACE,
                "claim": (
                    "Simulated ML observation: packet-set identity holds "
                    "across three local subjects."
                ),
                "evidence": [{"kind": "test", "uri": "artifact://sim/ml/observation"}],
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
        env=_env_for(home),
    )
    response = _json_from_output(result.stdout)
    structured = response["result"]["structuredContent"]
    if response["result"].get("isError"):
        raise RuntimeError(f"subject {label} propose failed: {structured}")
    packet_id = str(structured["packet_id"])
    print(f"[{label}] proposed packet_id={packet_id} namespace={PROPOSE_NAMESPACE}")
    return packet_id


def _start_server(subject: Subject) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-m", "aafp_commons.w1", "serve", "--port", str(subject.port)],
        env=_env_for(subject.home),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _wait_for_world(port: int, deadline: float | None = None) -> dict[str, Any]:
    if deadline is None:
        deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/world", timeout=0.25) as response:
                return json.load(response)
        except (OSError, ValueError):
            time.sleep(0.05)
    raise AssertionError(f"server did not become ready on port {port}")


def _replicate(home: str, port: int, peer_port: int) -> dict[str, Any]:
    request = Request(
        f"http://127.0.0.1:{port}/replicate",
        data=json.dumps({"peer": f"http://127.0.0.1:{peer_port}"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def _print_world(label: str, world: dict[str, Any], phase: str) -> None:
    missing = WORLD_FIELDS - set(world)
    if missing:
        raise RuntimeError(f"subject {label} /world missing fields {sorted(missing)}")
    print(f"[{label}] /world ({phase}) packet_count={world['packet_count']} "
          f"posture={world['posture']} "
          f"packet_set_merkle={world['packet_set_merkle']}")
    print(json.dumps(world, indent=2, sort_keys=True))


def _json_from_output(output: str) -> dict[str, Any]:
    start = output.find("{")
    if start < 0:
        raise RuntimeError(f"no JSON object in output: {output!r}")
    return json.loads(output[start:])


def main() -> int:
    print("W9 simulation harness: three local subjects A/B/C")
    _reset_homes()

    subjects: list[Subject] = []
    for label, home in zip(SUBJECTS, HOMES, strict=True):
        _init_subject(label, home)
        subjects.append(Subject(label=label, home=home, port=_free_port()))

    # Subject A proposes one evidence-backed packet; B and C start empty.
    packet_id = _propose_via_mcp(subjects[0].label, subjects[0].home)

    processes: list[subprocess.Popen[str]] = []
    try:
        for subject in subjects:
            processes.append(_start_server(subject))

        print("\n--- phase 1: /world before replication ---")
        worlds_before: dict[str, dict[str, Any]] = {}
        for subject in subjects:
            world = _wait_for_world(subject.port)
            worlds_before[subject.label] = world
            _print_world(subject.label, world, "before")

        if worlds_before["A"]["packet_count"] != 1:
            raise RuntimeError(
                "subject A expected 1 packet before replication, got "
                f"{worlds_before['A']['packet_count']}"
            )
        for label in ("B", "C"):
            if worlds_before[label]["packet_count"] != 0:
                raise RuntimeError(f"subject {label} expected 0 packets before replication")

        # Pull A's packet into B and C through the existing W3 loopback path.
        print("\n--- phase 2: loopback replication A -> B, A -> C ---")
        port_a = subjects[0].port
        for subject in subjects[1:]:
            result = _replicate(subject.home, subject.port, port_a)
            if not result.get("ok"):
                raise RuntimeError(f"replication into {subject.label} failed: {result}")
            print(f"[{subject.label}] replicate accepted={result.get('accepted')} "
                  f"already_present={result.get('already_present')}")

        print("\n--- phase 3: /world after replication ---")
        worlds_after: dict[str, dict[str, Any]] = {}
        for subject in subjects:
            world = _wait_for_world(subject.port)
            worlds_after[subject.label] = world
            _print_world(subject.label, world, "after")

        merkles = {label: worlds_after[label]["packet_set_merkle"] for label in SUBJECTS}
        if len(set(merkles.values())) != 1:
            raise RuntimeError(f"packet_set_merkle diverged after replication: {merkles}")
        for label in SUBJECTS:
            if worlds_after[label]["packet_count"] != 1:
                raise RuntimeError(
                    f"subject {label} expected 1 packet after replication, got "
                    f"{worlds_after[label]['packet_count']}"
                )

        print(f"\nall three subjects share packet_set_merkle={merkles['A']}")
        print(f"proposed packet_id={packet_id}")
        print(
            "ledgers left intact under "
            "/tmp/commons-sim-A, /tmp/commons-sim-B, /tmp/commons-sim-C"
        )
        return 0
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
