"""W11 three-subject evidence packet run.

Boots three independent Commons subjects (A, B, C) against isolated
``COMMONS_HOME`` directories under ``/tmp/commons-sim-*``, drives them through
the existing W1 CLI and W2 MCP surfaces to produce an evidence-backed
observation (A), a support observation (B), and a deterministic Resolution
packet (C), then replicates all packets through the existing W3 loopback HTTP
path so all three worlds converge on identical ``packet_set_merkle`` and
exactly one identical ``resolution_id``.

Run from the project root:

    uv run --no-sync python scripts/sim_packets.py

The script uses only existing surfaces (``commons init``, ``commons mcp``
``commons_propose``, ``commons serve`` ``/world`` and ``/replicate``). It
introduces no new CLI subcommands, no new MCP tool names, no transport, and no
packaging. Packet namespaces stay under ``commons/sim/ml/``.

Resolution packets use ``kind=finding`` with ``namespace=commons/sim/ml/resolution``
because built-in constitutions do not admit a literal ``resolution`` kind. The
resolution payload is carried in the packet ``scope`` and the ``resolution_id``
is computed using the existing ``ResolutionPacket`` formula from
``src/aafp_commons/mesh.py``.
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

from aafp_commons.mesh import ResolutionPacket

HOMES: tuple[str, str, str] = (
    "/tmp/commons-sim-A",
    "/tmp/commons-sim-B",
    "/tmp/commons-sim-C",
)
SUBJECTS: tuple[str, str, str] = ("A", "B", "C")
OBSERVATION_NAMESPACE = "commons/sim/ml/observation"
RESOLUTION_NAMESPACE = "commons/sim/ml/resolution"
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

# W10 ML evidence index artifacts — exact paths and sha256 digests verified
# during the W10 scan. A cites the v4 training summary; B cites the base model
# HumanEval results. Both are real files under /Users/david/Projects/.
ARTIFACT_A_PATH = "/Users/david/Projects/claude-yolo-v4-doc/results/summary.json"
ARTIFACT_A_DIGEST = "sha256:85f7671242a727d5b52a4ef7e16a0a808fa2265f4452663b6e2013a2ff24955d"
ARTIFACT_B_PATH = (
    "/Users/david/Projects/claude-yolo-v4-doc/eval-results/"
    "Qwen--Qwen2.5-Coder-7B-Instruct_humaneval_results.json"
)
ARTIFACT_B_DIGEST = "sha256:90401b8e26c663a56de35ac5edea60e21306bebc68844df9ab7d4638e5725c67"

# B supports A: both artifacts come from the same v4 training pipeline and do
# not genuinely disagree. A claims the fine-tuned 88.4% pass@1; B confirms the
# base model HumanEval evaluation that established the baseline.
RESOLUTION_DECISION = "a-preferred"


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


def _json_from_output(output: str) -> dict[str, Any]:
    start = output.find("{")
    if start < 0:
        raise RuntimeError(f"no JSON object in output: {output!r}")
    return json.loads(output[start:])


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


def _propose_via_mcp(label: str, home: str, arguments: dict[str, Any]) -> str:
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "commons_propose", "arguments": arguments},
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
    print(f"[{label}] proposed packet_id={packet_id} namespace={arguments['namespace']}")
    return packet_id


def _propose_observation_a(label: str, home: str) -> str:
    return _propose_via_mcp(
        label,
        home,
        {
            "kind": "observation",
            "namespace": OBSERVATION_NAMESPACE,
            "claim": (
                "The claude-yolo-vibes-v4 SFT+DPO training pipeline achieved "
                "88.4% HumanEval pass@1, recorded in results/summary.json."
            ),
            "scope": {
                "artifact_path": ARTIFACT_A_PATH,
                "artifact_digest": ARTIFACT_A_DIGEST,
                "metric": "humaneval-pass-at-1",
                "value": "88.4%",
            },
            "evidence": [
                {
                    "kind": "indexed-file",
                    "uri": f"file://{ARTIFACT_A_PATH}",
                    "digest": ARTIFACT_A_DIGEST,
                    "summary": (
                        "v4 training summary: SFT 2423 examples, "
                        "DPO 1031 pairs, HumanEval 88.4%"
                    ),
                }
            ],
            "confidence": 0.95,
        },
    )


def _propose_observation_b(label: str, home: str) -> str:
    return _propose_via_mcp(
        label,
        home,
        {
            "kind": "observation",
            "namespace": OBSERVATION_NAMESPACE,
            "claim": (
                "The v4 training pipeline evaluated the base "
                "Qwen2.5-Coder-7B-Instruct model on HumanEval, establishing "
                "the baseline for the fine-tuned 88.4% pass@1 result."
            ),
            "scope": {
                "artifact_path": ARTIFACT_B_PATH,
                "artifact_digest": ARTIFACT_B_DIGEST,
                "metric": "humaneval-base-eval",
                "supports": "observation-a",
            },
            "evidence": [
                {
                    "kind": "indexed-file",
                    "uri": f"file://{ARTIFACT_B_PATH}",
                    "digest": ARTIFACT_B_DIGEST,
                    "summary": "Base model HumanEval results (baseline for v4 fine-tune)",
                }
            ],
            "confidence": 0.9,
        },
    )


def _compute_resolution_id(
    observation_a_id: str,
    observation_b_id: str,
    artifact_a_digest: str,
    artifact_b_digest: str,
    conflict_ids: tuple[str, ...],
    decision: str,
) -> str:
    """Compute resolution_id using the existing ResolutionPacket formula."""
    resolution = ResolutionPacket(
        observation_a_id=observation_a_id,
        observation_b_id=observation_b_id,
        artifact_a_digest=artifact_a_digest,
        artifact_b_digest=artifact_b_digest,
        conflict_ids=conflict_ids,
        resolution=decision,
        reasoning=(
            "B supports A; both cite real indexed ML artifacts with matching "
            "sha256 digests from the W10 evidence index."
        ),
    )
    return resolution.resolution_id


def _propose_resolution_c(
    label: str, home: str, observation_a_id: str, observation_b_id: str
) -> str:
    resolution_id = _compute_resolution_id(
        observation_a_id,
        observation_b_id,
        ARTIFACT_A_DIGEST,
        ARTIFACT_B_DIGEST,
        (),
        RESOLUTION_DECISION,
    )
    return _propose_via_mcp(
        label,
        home,
        {
            "kind": "finding",
            "namespace": RESOLUTION_NAMESPACE,
            "claim": (
                f"Resolution {RESOLUTION_DECISION}: observation A is affirmed "
                f"by observation B's supporting evidence; both cite real "
                f"indexed ML artifacts with matching sha256 digests."
            ),
            "scope": {
                "observation_a_id": observation_a_id,
                "observation_b_id": observation_b_id,
                "artifact_a_digest": ARTIFACT_A_DIGEST,
                "artifact_b_digest": ARTIFACT_B_DIGEST,
                "conflict_ids": [],
                "decision": RESOLUTION_DECISION,
                "resolution_id": resolution_id,
            },
            "evidence": [
                {
                    "kind": "observation",
                    "uri": f"artifact://{OBSERVATION_NAMESPACE}/A",
                    "digest": observation_a_id,
                    "summary": "Subject A observation citing v4 training summary",
                },
                {
                    "kind": "observation",
                    "uri": f"artifact://{OBSERVATION_NAMESPACE}/B",
                    "digest": observation_b_id,
                    "summary": "Subject B support observation citing base model eval",
                },
            ],
            "confidence": 0.9,
        },
    )


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
          f"packet_set_merkle={world['packet_set_merkle']} "
          f"resolution_ids={world['resolution_ids']} "
          f"conflict_ids={world['conflict_ids']}")
    print(json.dumps(world, indent=2, sort_keys=True))


def main() -> int:
    print("W11 three-subject evidence packet run: A observation, B support, C resolution")
    _reset_homes()

    subjects: list[Subject] = []
    for label, home in zip(SUBJECTS, HOMES, strict=True):
        _init_subject(label, home)
        subjects.append(Subject(label=label, home=home, port=_free_port()))

    # A proposes an observation citing an exact indexed file path + sha256.
    packet_a = _propose_observation_a(subjects[0].label, subjects[0].home)

    # B proposes a support observation citing a different indexed artifact.
    packet_b = _propose_observation_b(subjects[1].label, subjects[1].home)

    # C proposes a deterministic Resolution packet citing both observation IDs.
    packet_c = _propose_resolution_c(
        subjects[2].label, subjects[2].home, packet_a, packet_b
    )

    print("\npacket IDs:")
    print(f"  A observation:  {packet_a}")
    print(f"  B observation:  {packet_b}")
    print(f"  C resolution:   {packet_c}")

    # Compute the expected resolution_id for verification.
    expected_resolution_id = _compute_resolution_id(
        packet_a, packet_b, ARTIFACT_A_DIGEST, ARTIFACT_B_DIGEST, (), RESOLUTION_DECISION
    )
    print(f"  resolution_id:  {expected_resolution_id}")
    print(f"  decision:       {RESOLUTION_DECISION}")

    processes: list[subprocess.Popen[str]] = []
    try:
        for subject in subjects:
            processes.append(_start_server(subject))

        print("\n--- phase 1: /world before replication ---")
        for subject in subjects:
            world = _wait_for_world(subject.port)
            _print_world(subject.label, world, "before")

        # Replicate so all three worlds converge on the same packet set.
        # A pulls from B (gets B), A pulls from C (gets C) → A has {A, B, C}.
        # B pulls from A (gets A, C) → B has {A, B, C}.
        # C pulls from A (gets A, B) → C has {A, B, C}.
        print("\n--- phase 2: loopback replication ---")
        port_a = subjects[0].port
        for peer_subject in subjects[1:]:
            result = _replicate(subjects[0].home, subjects[0].port, peer_subject.port)
            if not result.get("ok"):
                raise RuntimeError(f"replication A<-{peer_subject.label} failed: {result}")
            print(f"[A] replicate from {peer_subject.label} "
                  f"accepted={result.get('accepted')} "
                  f"already_present={result.get('already_present')}")

        for subject in subjects[1:]:
            result = _replicate(subject.home, subject.port, port_a)
            if not result.get("ok"):
                raise RuntimeError(f"replication {subject.label}<-A failed: {result}")
            print(f"[{subject.label}] replicate from A "
                  f"accepted={result.get('accepted')} "
                  f"already_present={result.get('already_present')}")

        print("\n--- phase 3: /world after replication ---")
        worlds_after: dict[str, dict[str, Any]] = {}
        for subject in subjects:
            world = _wait_for_world(subject.port)
            worlds_after[subject.label] = world
            _print_world(subject.label, world, "after")

        # Verify all three share the same packet_set_merkle.
        merkles = {label: worlds_after[label]["packet_set_merkle"] for label in SUBJECTS}
        if len(set(merkles.values())) != 1:
            raise RuntimeError(f"packet_set_merkle diverged after replication: {merkles}")

        # Verify each has exactly 3 packets.
        for label in SUBJECTS:
            if worlds_after[label]["packet_count"] != 3:
                raise RuntimeError(
                    f"subject {label} expected 3 packets after replication, got "
                    f"{worlds_after[label]['packet_count']}"
                )

        # Verify all three have exactly one identical resolution_id.
        all_resolution_ids: set[str] = set()
        for label in SUBJECTS:
            rids = worlds_after[label]["resolution_ids"]
            if len(rids) != 1:
                raise RuntimeError(
                    f"subject {label} expected exactly 1 resolution_id, got {rids}"
                )
            all_resolution_ids.update(rids)
        if len(all_resolution_ids) != 1:
            raise RuntimeError(f"resolution_ids diverged: {all_resolution_ids}")
        actual_resolution_id = next(iter(all_resolution_ids))
        if actual_resolution_id != expected_resolution_id:
            raise RuntimeError(
                f"resolution_id mismatch: actual={actual_resolution_id} "
                f"expected={expected_resolution_id}"
            )

        # Verify conflict_ids are preserved (empty in this support run).
        for label in SUBJECTS:
            if worlds_after[label]["conflict_ids"] != []:
                raise RuntimeError(
                    f"subject {label} expected empty conflict_ids, got "
                    f"{worlds_after[label]['conflict_ids']}"
                )

        print(f"\nall three subjects share packet_set_merkle={merkles['A']}")
        print(f"all three subjects share resolution_id={actual_resolution_id}")
        print(f"resolution decision: {RESOLUTION_DECISION}")
        print(f"packet IDs: A={packet_a} B={packet_b} C={packet_c}")
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
