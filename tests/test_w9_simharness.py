from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SIM_HOMES = (
    Path("/tmp/commons-sim-A"),
    Path("/tmp/commons-sim-B"),
    Path("/tmp/commons-sim-C"),
)
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
}


def _run_harness() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "sim_agents.py")],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "COMMONS_HOME": "/tmp/commons-sim-unused-do-not-create"},
        timeout=60,
    )


def test_sim_harness_exits_zero_and_converges_packet_set_merkle() -> None:
    result = _run_harness()
    assert result.returncode == 0, result.stderr + result.stdout
    assert "all three subjects share packet_set_merkle=" in result.stdout
    # Three distinct subject inits.
    assert result.stdout.count("posture=subject") >= 6  # three before + three after /world lines
    assert "commons/sim/ml/observation" in result.stdout


def test_sim_harness_leaves_ledgers_intact_and_no_commons_home() -> None:
    commons_home = Path.home().joinpath(".commons")
    existed_before = commons_home.exists()
    _run_harness()
    for home in SIM_HOMES:
        assert (home / "identity.json").exists()
        assert (home / "constitution.json").exists()
        assert (home / "objects").is_dir()
        assert (home / "ledger.jsonl").exists()
    # The harness must not create or touch ~/.commons.
    assert commons_home.exists() == existed_before


def test_sim_harness_introduces_no_new_mcp_names_or_subcommands() -> None:
    source = (PROJECT_ROOT / "scripts" / "sim_agents.py").read_text(encoding="utf-8")
    # Only existing surfaces are allowed.
    for forbidden in ("commons mcp propose", "quic", "vast", "brew", "npm", "hatchling"):
        assert forbidden not in source
    # The harness must not create new MCP tool names; it only calls commons_propose.
    assert "commons_propose" in source
    # Packet namespace stays under commons/sim/ml/.
    assert "commons/sim/ml/" in source


def test_w9_contract_exists() -> None:
    assert (PROJECT_ROOT / "contracts" / "W9-simharness.md").exists()
