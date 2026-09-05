"""Commons Mesh v0 wire contracts.

Schemas for the gossip protocol that connects independent Commons nodes.
These are signed, content-addressed messages exchanged over HTTP on :8080.

No trusted coordinator. Each node signs its own messages with its Ironclad
identity. Verification is mandatory on receipt.

Wire format: JSON envelope with a type discriminator and an Ironclad signature.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from aafp_commons.canonical import digest

MESH_SCHEMA = "aafp.commons/mesh-v0"

MeshMessageType = Literal[
    "heartbeat", "tip-gossip", "conflict",
    "replica-request", "replica-response",
]


@dataclass(frozen=True)
class Heartbeat:
    """Signed node liveness announcement. Broadcast every 5s.

    v0.2: carries packet_set_merkle and fork_ids so peers can detect
    fork convergence without fetching blocks.
    """
    agent_id: str
    node_role: str
    ledger_height: int
    ledger_tip: str
    peer_count: int
    packet_set_merkle: str = ""
    fork_ids: tuple[str, ...] = ()
    timestamp: int = field(default_factory=lambda: int(time.time()))
    schema: str = MESH_SCHEMA + "/heartbeat"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TipGossip:
    """Announce a newly admitted packet to peers. Sub-second propagation."""
    agent_id: str
    packet_id: str  # content address of the admitted packet
    block_height: int
    block_hash: str  # ledger block that committed this packet
    prev_block_hash: str
    policy_status: str  # "accepted", "rejected", "already-present"
    policy_reasons: tuple[str, ...] = ()
    evidence_count: int = 0
    timestamp: int = field(default_factory=lambda: int(time.time()))
    schema: str = MESH_SCHEMA + "/tip-gossip"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass(frozen=True)
class ConflictPacket:
    """Signed conflict declaration when two nodes admit contradictory claims.

    Does not rewrite history. Both packets remain in their ledgers. The
    conflict is itself a content-addressed object that the reconciliation
    node tracks.
    """
    agent_id: str  # the node that detected the conflict
    packet_a_id: str  # first conflicting claim
    packet_b_id: str  # second conflicting claim
    conflict_kind: str  # "contradiction", "duplicate-claim", "supersede-chain-break"
    evidence: tuple[str, ...] = ()  # content addresses of evidence objects
    resolution: str = "unresolved"  # "unresolved", "a-preferred", "b-preferred", "both-rejected"
    timestamp: int = field(default_factory=lambda: int(time.time()))
    schema: str = MESH_SCHEMA + "/conflict"

    @property
    def conflict_id(self) -> str:
        """Stable ID based on the conflicting packet pair, not the detector.

        Two nodes detecting the same contradiction produce the same conflict_id.
        """
        pair = sorted([self.packet_a_id, self.packet_b_id])
        return digest({"packets": pair, "kind": self.conflict_kind})

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    def to_dict_with_id(self) -> dict[str, Any]:
        d = asdict(self)
        d["conflict_id"] = self.conflict_id
        return d


@dataclass(frozen=True)
class ReplicaRequest:
    """Ask a peer for packets since a given block height. For resumable replication."""
    agent_id: str
    since_height: int
    timestamp: int = field(default_factory=lambda: int(time.time()))
    schema: str = MESH_SCHEMA + "/replica-request"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReplicaResponse:
    """Peer responds with blocks and packets since the requested height."""
    agent_id: str
    blocks: list[dict[str, Any]]  # SignedBlock dicts
    packets: list[dict[str, Any]]  # SignedPacket dicts
    timestamp: int = field(default_factory=lambda: int(time.time()))
    schema: str = MESH_SCHEMA + "/replica-response"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResolutionPacket:
    """Signed resolution from the reconciliation node.

    Does NOT delete observations. It is another ledger object that records
    the reconciler's verdict on a pair of contradictory observations.

    Rule (frozen in v0.3):
      |tok_s_A - tok_s_B| / max(tok_s) <= 0.15  → incomparable
      else prefer the artifact whose recipe_digest matches the frozen contract
      if NEITHER matches recipe → both-rejected
    """
    observation_a_id: str
    observation_b_id: str
    artifact_a_digest: str
    artifact_b_digest: str
    conflict_ids: tuple[str, ...]  # both conflict ids being resolved
    resolution: str  # "a-preferred", "b-preferred", "both-rejected", "incomparable"
    reasoning: str  # human-readable explanation
    tok_s_a: float = 0.0
    tok_s_b: float = 0.0
    recipe_digest: str = ""
    schema: str = MESH_SCHEMA + "/resolution"

    @property
    def resolution_id(self) -> str:
        """Stable ID — same on every node that stores the same resolution."""
        return digest({
            "observation_a_id": self.observation_a_id,
            "observation_b_id": self.observation_b_id,
            "artifact_a_digest": self.artifact_a_digest,
            "artifact_b_digest": self.artifact_b_digest,
            "conflict_ids": list(self.conflict_ids),
            "resolution": self.resolution,
        })

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["resolution_id"] = self.resolution_id
        return d


@dataclass(frozen=True)
class ForkRecord:
    """Canonical fork declaration. Content-addressed over the WORLD state.

    v0.2: fork_id is digest of {packet_set_merkle, tips, conflict_ids} —
    NOT over agent_id, timestamp, or detect-time. Two nodes observing the
    same world state produce the SAME fork_id. This is the "one fork" in
    "One World or One Fork."

    The fork record is published to the ledger as kind=finding,
    namespace=commons/mesh/fork, so it becomes part of canonical history.
    """
    packet_set_merkle: str  # merkle root of sorted packet IDs
    tips: tuple[tuple[str, str], ...]  # sorted [(agent_id, tip_hash), ...]
    conflict_ids: tuple[str, ...]  # sorted conflict IDs active in this fork
    reason: str = "independent-signing-keys"
    schema: str = MESH_SCHEMA + "/fork-record"

    @property
    def fork_id(self) -> str:
        """Canonical ID — same on every node that sees the same world."""
        return digest({
            "packet_set_merkle": self.packet_set_merkle,
            "tips": list(self.tips),
            "conflict_ids": list(self.conflict_ids),
        })

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["fork_id"] = self.fork_id
        return d

    def to_canonical_dict(self) -> dict[str, Any]:
        """The fields that go into fork_id — no agent_id, no timestamp."""
        return {
            "packet_set_merkle": self.packet_set_merkle,
            "tips": list(self.tips),
            "conflict_ids": list(self.conflict_ids),
            "reason": self.reason,
            "schema": self.schema,
        }


@dataclass(frozen=True)
class MeshEnvelope:
    """Signed wrapper for any mesh message. The wire format."""
    message_type: MeshMessageType
    message: dict[str, Any]
    signer_key_id: str
    signer_public_key_b64: str
    signature_b64: str
    signed_at: int = field(default_factory=lambda: int(time.time()))
    schema: str = MESH_SCHEMA + "/envelope"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
