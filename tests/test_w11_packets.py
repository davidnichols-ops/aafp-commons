from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ironclad.trust import Identity

from aafp_commons.mesh import ResolutionPacket
from aafp_commons.models import EvidenceRef, KnowledgePacket, MethodRef
from aafp_commons.repository import CommonsRepository
from aafp_commons.w1 import RESOLUTION_NAMESPACE, world

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

ARTIFACT_A_DIGEST = "sha256:85f7671242a727d5b52a4ef7e16a0a808fa2265f4452663b6e2013a2ff24955d"
ARTIFACT_B_DIGEST = "sha256:90401b8e26c663a56de35ac5edea60e21306bebc68844df9ab7d4638e5725c67"


def _run_harness() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "sim_packets.py")],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "COMMONS_HOME": "/tmp/commons-sim-unused-do-not-create"},
        timeout=90,
    )


def test_sim_packets_exits_zero_and_converges() -> None:
    result = _run_harness()
    assert result.returncode == 0, result.stderr + result.stdout
    assert "all three subjects share packet_set_merkle=" in result.stdout
    assert "all three subjects share resolution_id=" in result.stdout
    assert "resolution decision: a-preferred" in result.stdout
    # Three distinct subject inits.
    assert result.stdout.count("posture=subject") >= 6
    # All three packet namespaces under commons/sim/ml/.
    assert "commons/sim/ml/observation" in result.stdout
    assert "commons/sim/ml/resolution" in result.stdout


def test_sim_packets_leaves_ledgers_intact_and_no_commons_home() -> None:
    commons_home = Path.home().joinpath(".commons")
    existed_before = commons_home.exists()
    _run_harness()
    for home in SIM_HOMES:
        assert (home / "identity.json").exists()
        assert (home / "constitution.json").exists()
        assert (home / "objects").is_dir()
        assert (home / "ledger.jsonl").exists()
    assert commons_home.exists() == existed_before


def test_sim_packets_no_new_mcp_names_or_forbidden_patterns() -> None:
    source = (PROJECT_ROOT / "scripts" / "sim_packets.py").read_text(encoding="utf-8")
    for forbidden in ("commons mcp propose", "quic", "vast", "brew", "npm", "hatchling"):
        assert forbidden not in source
    assert "commons_propose" in source
    assert "commons/sim/ml/" in source


def test_w11_contract_exists() -> None:
    assert (PROJECT_ROOT / "contracts" / "W11-packets.md").exists()


def test_resolution_id_is_deterministic_and_matches_mesh_formula() -> None:
    """The resolution_id in the sim scope matches mesh.ResolutionPacket.resolution_id."""
    observation_a_id = "sha256:" + "a" * 64
    observation_b_id = "sha256:" + "b" * 64
    conflict_ids: tuple[str, ...] = ()
    decision = "a-preferred"

    resolution = ResolutionPacket(
        observation_a_id=observation_a_id,
        observation_b_id=observation_b_id,
        artifact_a_digest=ARTIFACT_A_DIGEST,
        artifact_b_digest=ARTIFACT_B_DIGEST,
        conflict_ids=conflict_ids,
        resolution=decision,
        reasoning="test",
    )
    expected = resolution.resolution_id
    # Same inputs always produce the same ID.
    assert expected == ResolutionPacket(
        observation_a_id=observation_a_id,
        observation_b_id=observation_b_id,
        artifact_a_digest=ARTIFACT_A_DIGEST,
        artifact_b_digest=ARTIFACT_B_DIGEST,
        conflict_ids=conflict_ids,
        resolution=decision,
        reasoning="different reasoning does not change the ID",
    ).resolution_id
    # Different decision produces a different ID.
    other = ResolutionPacket(
        observation_a_id=observation_a_id,
        observation_b_id=observation_b_id,
        artifact_a_digest=ARTIFACT_A_DIGEST,
        artifact_b_digest=ARTIFACT_B_DIGEST,
        conflict_ids=conflict_ids,
        resolution="b-preferred",
        reasoning="test",
    ).resolution_id
    assert expected != other


def test_world_projection_extracts_resolution_id_from_scope(tmp_path: Path) -> None:
    """world() projects resolution_ids from stored commons/sim/ml/resolution packets."""
    home = tmp_path / "home"
    identity = Identity.generate()
    repository = CommonsRepository(home)
    repository.initialize()
    constitution = repository.install_constitution(
        __import__(
            "aafp_commons.packages.grok_truth_seeking",
            fromlist=["GROK_TRUTH_SEEKING_MANIFEST"],
        ).GROK_TRUTH_SEEKING_MANIFEST
    )
    # Install identity so world() reports subject posture.
    from aafp_commons.w1 import _save_identity
    _save_identity(home, identity)

    observation_a_id = "sha256:" + "a" * 64
    observation_b_id = "sha256:" + "b" * 64
    resolution = ResolutionPacket(
        observation_a_id=observation_a_id,
        observation_b_id=observation_b_id,
        artifact_a_digest=ARTIFACT_A_DIGEST,
        artifact_b_digest=ARTIFACT_B_DIGEST,
        conflict_ids=(),
        resolution="a-preferred",
        reasoning="test resolution",
    )
    packet = KnowledgePacket(
        kind="finding",
        namespace=RESOLUTION_NAMESPACE,
        claim="Resolution a-preferred: observation A is affirmed by observation B.",
        scope={
            "observation_a_id": observation_a_id,
            "observation_b_id": observation_b_id,
            "artifact_a_digest": ARTIFACT_A_DIGEST,
            "artifact_b_digest": ARTIFACT_B_DIGEST,
            "conflict_ids": [],
            "decision": "a-preferred",
            "resolution_id": resolution.resolution_id,
        },
        evidence=(
            EvidenceRef(
                kind="observation",
                uri="artifact://commons/sim/ml/observation/A",
                digest=observation_a_id,
            ),
            EvidenceRef(
                kind="observation",
                uri="artifact://commons/sim/ml/observation/B",
                digest=observation_b_id,
            ),
        ),
        confidence=0.9,
        author_agent_id="aafp:" + "0" * 64,
        constitution=constitution,
        method=MethodRef("w11-test", "1.0"),
    )
    from aafp_commons.signing import sign_packet
    decision = repository.submit(sign_packet(packet, identity), identity)
    assert decision.accepted

    result = world(home)
    assert set(result) == WORLD_FIELDS
    assert result["resolution_ids"] == [resolution.resolution_id]
    assert result["conflict_ids"] == []


def test_world_projection_empty_without_resolution_packets(tmp_path: Path) -> None:
    """world() returns empty conflict_ids and resolution_ids when no sim packets exist."""
    home = tmp_path / "home"
    identity = Identity.generate()
    repository = CommonsRepository(home)
    repository.initialize()
    constitution = repository.install_constitution(
        __import__(
            "aafp_commons.packages.grok_truth_seeking",
            fromlist=["GROK_TRUTH_SEEKING_MANIFEST"],
        ).GROK_TRUTH_SEEKING_MANIFEST
    )
    from aafp_commons.w1 import _save_identity
    _save_identity(home, identity)

    # Submit a non-resolution packet.
    packet = KnowledgePacket(
        kind="observation",
        namespace="commons/sim/ml/observation",
        claim="A test observation that is not a resolution packet.",
        scope={"test": True},
        evidence=(EvidenceRef(kind="test", uri="artifact://test"),),
        confidence=0.5,
        author_agent_id="aafp:" + "1" * 64,
        constitution=constitution,
        method=MethodRef("test", "1.0"),
    )
    from aafp_commons.signing import sign_packet
    repository.submit(sign_packet(packet, identity), identity)

    result = world(home)
    assert result["resolution_ids"] == []
    assert result["conflict_ids"] == []


def test_world_projection_deterministic_across_calls(tmp_path: Path) -> None:
    """The same packet set always produces the same projected IDs."""
    home = tmp_path / "home"
    identity = Identity.generate()
    repository = CommonsRepository(home)
    repository.initialize()
    constitution = repository.install_constitution(
        __import__(
            "aafp_commons.packages.grok_truth_seeking",
            fromlist=["GROK_TRUTH_SEEKING_MANIFEST"],
        ).GROK_TRUTH_SEEKING_MANIFEST
    )
    from aafp_commons.w1 import _save_identity
    _save_identity(home, identity)

    observation_a_id = "sha256:" + "c" * 64
    observation_b_id = "sha256:" + "d" * 64
    resolution = ResolutionPacket(
        observation_a_id=observation_a_id,
        observation_b_id=observation_b_id,
        artifact_a_digest=ARTIFACT_A_DIGEST,
        artifact_b_digest=ARTIFACT_B_DIGEST,
        conflict_ids=(),
        resolution="incomparable",
        reasoning="determinism test",
    )
    packet = KnowledgePacket(
        kind="finding",
        namespace=RESOLUTION_NAMESPACE,
        claim="Resolution incomparable: the two observations cannot be ranked.",
        scope={
            "observation_a_id": observation_a_id,
            "observation_b_id": observation_b_id,
            "artifact_a_digest": ARTIFACT_A_DIGEST,
            "artifact_b_digest": ARTIFACT_B_DIGEST,
            "conflict_ids": [],
            "decision": "incomparable",
            "resolution_id": resolution.resolution_id,
        },
        evidence=(
            EvidenceRef(kind="observation", uri="artifact://test/a", digest=observation_a_id),
            EvidenceRef(kind="observation", uri="artifact://test/b", digest=observation_b_id),
        ),
        confidence=0.8,
        author_agent_id="aafp:" + "2" * 64,
        constitution=constitution,
        method=MethodRef("determinism-test", "1.0"),
    )
    from aafp_commons.signing import sign_packet
    repository.submit(sign_packet(packet, identity), identity)

    first = world(home)
    second = world(home)
    assert first["resolution_ids"] == second["resolution_ids"]
    assert first["conflict_ids"] == second["conflict_ids"]


def test_sim_packets_observation_a_cites_exact_indexed_path_and_digest() -> None:
    """A's observation must cite an exact W10 indexed file path and its sha256 digest."""
    source = (PROJECT_ROOT / "scripts" / "sim_packets.py").read_text(encoding="utf-8")
    assert "/Users/david/Projects/claude-yolo-v4-doc/results/summary.json" in source
    assert ARTIFACT_A_DIGEST in source
    assert ARTIFACT_B_DIGEST in source
