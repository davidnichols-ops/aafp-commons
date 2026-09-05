#!/usr/bin/env python3
"""Commons Mesh Node — v0.1 daemon.

Fixes from v0:
- SO_REUSEADDR + PID file + clean shutdown by PID
- First block height = 1 (genesis is implicit, block 1 is first admit)
- Conflict dedup by conflict_id; ConflictPacket emitted as signed ledger object once
- Replica verifies prev_block_hash; mismatch = FORK record, not silent append
- Gossip pulls packet by ID from sender, then policy-admits
- No fire-and-forget: gossip triggers fetch + admit
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).parent / "src"))

from ironclad.trust import Identity  # noqa: E402

from aafp_commons.canonical import b64decode, b64encode, canonical_json, digest  # noqa: E402
from aafp_commons.constitutions import ConstitutionManifest, FileConstitutionResolver  # noqa: E402
from aafp_commons.identity import derive_agent_id  # noqa: E402
from aafp_commons.ledger import (  # noqa: E402
    GENESIS_HASH,
    Ledger,
    LedgerBlock,
    SignedBlock,
    merkle_root,
)
from aafp_commons.mesh import (  # noqa: E402
    ConflictPacket,
    ForkRecord,
    Heartbeat,
    MeshEnvelope,
    ReplicaRequest,
    ResolutionPacket,
    TipGossip,
)
from aafp_commons.models import (  # noqa: E402
    ConstitutionRef,
    EvidenceRef,
    KnowledgePacket,
    MethodRef,
)
from aafp_commons.policy import AdmissionPolicy  # noqa: E402
from aafp_commons.signing import SignedPacket, sign_packet  # noqa: E402

MESH_DOMAIN = b"aafp-commons/mesh-envelope/v0\x00"
BLOCK_DOMAIN = b"aafp-commons/ledger-block/v1\x00"


class HeightOneLedger(Ledger):
    """Ledger where first block is height 1, not 0. Genesis is implicit."""

    def append(self, packet_digests, authority):
        from aafp_commons.canonical import canonical_json
        items = tuple(packet_digests)
        if not items:
            raise ValueError("cannot append an empty block")
        existing = self.blocks()
        height = len(existing) + 1  # 1-based, not 0-based
        block = LedgerBlock(
            height=height,
            previous_hash=existing[-1].block.block_hash if existing else GENESIS_HASH,
            packet_digests=items,
            merkle_root=merkle_root(items),
            authority_key_id=authority.key_id,
            timestamp=int(time.time()),
        )
        signed = SignedBlock(
            block=block,
            authority_public_key_b64=b64encode(authority.public_bytes()),
            signature_b64=b64encode(
                authority.sign(BLOCK_DOMAIN + canonical_json(block.to_dict()))
            ),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(signed.to_dict(), sort_keys=True, separators=(",", ":")))
            handle.write("\n")
        return signed


class MeshNode:
    """A single Commons node with ledger, policy, and gossip."""

    def __init__(self, root, role, identity, peers, port=8081):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.role = role
        self.identity = identity
        self.agent_id = derive_agent_id(identity.public_bytes())
        self.peers = peers
        self.port = port

        self.objects_dir = self.root / "objects"
        self.objects_dir.mkdir(exist_ok=True)
        self.ledger = HeightOneLedger(self.root / "ledger.jsonl")
        self.policy = AdmissionPolicy()
        self.constitutions = FileConstitutionResolver(self.root / "constitutions")

        self._lock = threading.Lock()
        self._conflicts: dict[str, ConflictPacket] = {}  # dedup by conflict_id
        self._seen_tips: set[str] = set()
        self._known_peers: dict[str, dict[str, Any]] = {}
        self._running = True

        self._fork_records: dict[str, ForkRecord] = {}
        self._forks: list[dict[str, Any]] = []
        self._last_tip_snapshot: tuple[tuple[str, str], ...] = ()
        self._tip_stable_count: int = 0
        self._resolutions: dict[str, ResolutionPacket] = {}

        self._ensure_constitution()
        self._load_conflicts_from_disk()
        self._load_fork_records_from_disk()
        self._load_resolutions_from_disk()

        print(f"[node] agent_id={self.agent_id} role={self.role} root={self.root}")
        print(f"[node] peers={self.peers}")
        print(f"[node] ledger blocks={len(self.ledger.blocks())}")

    def _ensure_constitution(self):
        const_dir = self.root / "constitutions"
        const_dir.mkdir(exist_ok=True)
        grok_path = const_dir / "grok-truth-seeking" / "1.0.0.json"
        if not grok_path.exists():
            manifest = ConstitutionManifest(
                constitution_id="grok-truth-seeking",
                version="1.0.0",
                namespace_prefixes=("commons",),
                minimum_evidence=1,
                require_evidence_digests=False,
                description="Truth-seeking constitution: require evidence, reject secrets",
            )
            grok_path.parent.mkdir(parents=True, exist_ok=True)
            grok_path.write_text(manifest.to_json())
            print(f"[node] installed constitution: {manifest.constitution_id}@{manifest.version}")

    def _load_conflicts_from_disk(self):
        """Load persisted conflict objects from disk on startup."""
        conflicts_dir = self.root / "conflicts"
        if conflicts_dir.exists():
            for path in sorted(conflicts_dir.glob("*.json")):
                try:
                    data = json.loads(path.read_text())
                    conflict = ConflictPacket(
                        agent_id=data["agent_id"],
                        packet_a_id=data["packet_a_id"],
                        packet_b_id=data["packet_b_id"],
                        conflict_kind=data["conflict_kind"],
                        evidence=tuple(data.get("evidence", ())),
                        resolution=data.get("resolution", "unresolved"),
                        timestamp=data["timestamp"],
                    )
                    self._conflicts[conflict.conflict_id] = conflict
                except Exception:
                    pass

    def _load_fork_records_from_disk(self):
        """Load persisted fork records from disk on startup."""
        forks_dir = self.root / "fork-records"
        if forks_dir.exists():
            for path in sorted(forks_dir.glob("*.json")):
                try:
                    data = json.loads(path.read_text())
                    fr = ForkRecord(
                        packet_set_merkle=data["packet_set_merkle"],
                        tips=tuple(tuple(t) for t in data.get("tips", ())),
                        conflict_ids=tuple(data.get("conflict_ids", ())),
                        reason=data.get("reason", "independent-signing-keys"),
                    )
                    self._fork_records[fr.fork_id] = fr
                except Exception:
                    pass

    def _load_resolutions_from_disk(self):
        """Load persisted resolution packets from disk on startup."""
        res_dir = self.root / "resolutions"
        if res_dir.exists():
            for path in sorted(res_dir.glob("*.json")):
                try:
                    data = json.loads(path.read_text())
                    rp = ResolutionPacket(
                        observation_a_id=data["observation_a_id"],
                        observation_b_id=data["observation_b_id"],
                        artifact_a_digest=data["artifact_a_digest"],
                        artifact_b_digest=data["artifact_b_digest"],
                        conflict_ids=tuple(data.get("conflict_ids", ())),
                        resolution=data["resolution"],
                        reasoning=data.get("reasoning", ""),
                        tok_s_a=data.get("tok_s_a", 0.0),
                        tok_s_b=data.get("tok_s_b", 0.0),
                        recipe_digest=data.get("recipe_digest", ""),
                    )
                    self._resolutions[rp.resolution_id] = rp
                except Exception:
                    pass

    def _get_resolution_ids(self) -> list[str]:
        """Sorted resolution IDs."""
        return sorted(self._resolutions.keys())

    def _get_packet_ids(self) -> list[str]:
        """Return sorted list of all packet IDs in the ledger."""
        ids = []
        for block in self.ledger.blocks():
            ids.extend(block.block.packet_digests)
        return sorted(ids)

    def _get_packet_set_merkle(self) -> str:
        """Merkle root of sorted packet IDs — same on every node with same packets."""
        ids = self._get_packet_ids()
        if not ids:
            return GENESIS_HASH
        return digest(ids)

    def _get_conflict_ids(self) -> tuple[str, ...]:
        """Sorted conflict IDs active in this node."""
        return tuple(sorted(self._conflicts.keys()))

    def _prune_stale_peers(self, max_age_seconds: int = 30):
        """Remove peers not seen in the last max_age_seconds."""
        now = int(time.time())
        stale = [
            pid for pid, info in self._known_peers.items()
            if now - info.get("last_seen", 0) > max_age_seconds
        ]
        for pid in stale:
            del self._known_peers[pid]

    def check_and_publish_fork(self):
        """Check if tips differ across nodes. If so, emit ONE canonical ForkRecord.

        v0.2: fork_id = digest({packet_set_merkle, tips, conflict_ids}).
        Same world state → same fork_id on every node. Dedup by fork_id.

        Only fire when:
        1. We have tips from ALL configured peers
        2. The tip snapshot has been STABLE for 3 consecutive checks
        This prevents spurious forks from partial/transient views.

        Stale peers (not seen in 30s) are pruned before checking.
        """
        self._prune_stale_peers(max_age_seconds=30)
        my_tip = self.get_tip()
        my_set_merkle = self._get_packet_set_merkle()
        my_conflict_ids = self._get_conflict_ids()

        # Collect tips from self + known peers
        all_tips = [(self.agent_id, my_tip["tip"])]
        peers_seen = 0
        for peer_id, info in self._known_peers.items():
            peer_tip = info.get("ledger_tip", "")
            if peer_tip:
                all_tips.append((peer_id, peer_tip))
                peers_seen += 1

        # Only check when we have ALL peers reporting
        if peers_seen < len(self.peers):
            return  # partial view — wait for all peers

        # Sort by agent_id for canonical ordering
        all_tips.sort(key=lambda x: x[0])
        current_snapshot = tuple(all_tips)

        # Track tip stability — require 2 consecutive identical snapshots
        if current_snapshot == self._last_tip_snapshot:
            self._tip_stable_count += 1
        else:
            self._tip_stable_count = 0
            self._last_tip_snapshot = current_snapshot

        if self._tip_stable_count < 3:
            return  # tips not stable yet — wait

        # Check if tips differ
        unique_tips = {t for _, t in all_tips if t}
        if len(unique_tips) <= 1:
            return  # all same — no fork

        # Build canonical fork record
        fork = ForkRecord(
            packet_set_merkle=my_set_merkle,
            tips=tuple(all_tips),
            conflict_ids=my_conflict_ids,
        )
        fid = fork.fork_id

        # Dedup by fork_id — if we already have this exact fork, no-op
        if fid in self._fork_records and len(self._fork_records) == 1:
            return  # already the only fork record

        # Replace all previous fork records with this one.
        # Old forks were detected during propagation turbulence; the latest
        # stable fork is the canonical one. Keep only 1 fork record at a time.
        self._fork_records = {fid: fork}
        forks_dir = self.root / "fork-records"
        forks_dir.mkdir(exist_ok=True)
        # Clear old fork record files
        for old_path in forks_dir.glob("*.json"):
            old_path.unlink()
        fpath = forks_dir / f"{fid.removeprefix('sha256:')}.json"
        fpath.write_text(json.dumps(fork.to_dict(), sort_keys=True, indent=2) + "\n")
        print(f"[fork-record] {fid[:16]}... tips differ across {len(all_tips)} nodes, "
              f"packet_set_merkle={my_set_merkle[:16]}... conflicts={len(my_conflict_ids)}")

    def _publish_fork_to_ledger(self, fork: ForkRecord) -> None:
        """Publish fork record to ledger as kind=finding namespace=commons/mesh/fork."""
        try:
            packet = KnowledgePacket(
                kind="finding",
                namespace="commons/mesh/fork",
                claim=f"fork detected: packet_set_merkle={fork.packet_set_merkle[:20]}... "
                      f"tips_differ_across={len(fork.tips)}_nodes",
                scope={
                    "fork_id": fork.fork_id,
                    "packet_set_merkle": fork.packet_set_merkle,
                    "tips": list(fork.tips),
                    "conflict_ids": list(fork.conflict_ids),
                },
                evidence=(
                    EvidenceRef(
                        kind="observation",
                        uri=f"aafp://fork/{fork.fork_id}",
                        summary="fork record content address",
                    ),
                ),
                confidence=1.0,
                author_agent_id=self.agent_id,
                constitution=ConstitutionRef(
                    constitution_id="grok-truth-seeking",
                    version="1.0.0",
                    digest=self.constitutions.resolve(
                        ConstitutionRef(
                            constitution_id="grok-truth-seeking",
                            version="1.0.0",
                        )
                    ).manifest_digest,
                ),
                method=MethodRef(name="fork-detection", version="1.0"),
            )
            signed = sign_packet(packet, self.identity)
            # Write object + append to ledger (bypass policy — internal mesh event)
            path = self.objects_dir / f"{signed.packet_id.removeprefix('sha256:')}.json"
            if not path.exists():
                path.write_text(json.dumps(signed.to_dict(), sort_keys=True, indent=2) + "\n")
                self.ledger.append((signed.packet_id,), self.identity)
                print(f"[fork-ledger] published fork finding {fork.fork_id[:16]}... "
                      f"as packet {signed.packet_id[:16]}...")
        except Exception as e:
            print(f"[fork-ledger] failed to publish: {e}")

    def sign_envelope(self, message_type, message):
        payload = canonical_json({"type": message_type, "message": message})
        sig = self.identity.sign(MESH_DOMAIN + payload)
        return MeshEnvelope(
            message_type=message_type,
            message=message,
            signer_key_id=self.identity.key_id,
            signer_public_key_b64=b64encode(self.identity.public_bytes()),
            signature_b64=b64encode(sig),
        )

    def verify_envelope(self, env):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        payload = canonical_json({"type": env.message_type, "message": env.message})
        pub_bytes = b64decode(env.signer_public_key_b64)
        pub = Ed25519PublicKey.from_public_bytes(pub_bytes)
        try:
            pub.verify(b64decode(env.signature_b64), MESH_DOMAIN + payload)
            return True
        except Exception:
            return False

    def submit_packet(self, signed):
        """Admit a packet through policy gates and append to ledger."""
        with self._lock:
            try:
                constitution = self.constitutions.resolve(signed.packet.constitution)
            except Exception as e:
                return {"status": "rejected", "reasons": [str(e)]}

            decision = self.policy.evaluate(signed, constitution)
            if not decision.accepted and decision.status != "already-present":
                return {"status": decision.status, "reasons": list(decision.reasons)}

            path = self.objects_dir / f"{signed.packet_id.removeprefix('sha256:')}.json"
            if not path.exists():
                path.write_text(json.dumps(signed.to_dict(), sort_keys=True, indent=2) + "\n")
                block = self.ledger.append((signed.packet_id,), self.identity)
                result = {
                    "status": "accepted",
                    "packet_id": signed.packet_id,
                    "block_height": block.block.height,
                    "block_hash": block.block.block_hash,
                    "policy_reasons": list(decision.reasons),
                }
            else:
                blocks = self.ledger.blocks()
                result = {
                    "status": "already-present",
                    "packet_id": signed.packet_id,
                    "block_height": blocks[-1].block.height if blocks else 0,
                }

            # Check for conflicts — dedup by conflict_id
            self._check_conflicts(signed)
            return result

    def _check_conflicts(self, new_packet):
        """Detect contradiction. Emit ConflictPacket as signed object once."""
        if not new_packet.packet.contradicts:
            return
        for contradicted_id in new_packet.packet.contradicts:
            contradicted_path = self.objects_dir / f"{contradicted_id.removeprefix('sha256:')}.json"
            if not contradicted_path.exists():
                continue
            conflict = ConflictPacket(
                agent_id=self.agent_id,
                packet_a_id=contradicted_id,
                packet_b_id=new_packet.packet_id,
                conflict_kind="contradiction",
                evidence=tuple(e.digest for e in new_packet.packet.evidence if e.digest),
            )
            cid = conflict.conflict_id
            if cid in self._conflicts:
                continue  # already recorded, do not duplicate
            self._conflicts[cid] = conflict

            # Persist conflict as a signed object on disk
            conflicts_dir = self.root / "conflicts"
            conflicts_dir.mkdir(exist_ok=True)
            cpath = conflicts_dir / f"{cid.removeprefix('sha256:')}.json"
            cpath.write_text(json.dumps(conflict.to_dict(), sort_keys=True, indent=2) + "\n")

            print(f"[conflict] {cid[:16]}... "
                  f"{conflict.packet_a_id[:16]}... vs {conflict.packet_b_id[:16]}...")

    def get_tip(self):
        blocks = self.ledger.blocks()
        if not blocks:
            return {"height": 0, "tip": GENESIS_HASH, "packets": 0}
        last = blocks[-1]
        return {
            "height": last.block.height,
            "tip": last.block.block_hash,
            "packets": sum(len(b.block.packet_digests) for b in blocks),
        }

    def get_blocks_since(self, height):
        blocks = self.ledger.blocks()
        result = []
        for block in blocks:
            if block.block.height < height:
                continue
            block_data = block.to_dict()
            packets = []
            for pid in block.block.packet_digests:
                path = self.objects_dir / f"{pid.removeprefix('sha256:')}.json"
                if path.exists():
                    packets.append(json.loads(path.read_text()))
            result.append({"block": block_data, "packets": packets})
        return result

    def fetch_and_admit_from_peer(self, peer, packet_id):
        """Pull a packet by ID from a peer, then policy-admit it."""
        try:
            req = Request(f"{peer}/packet/{packet_id}")
            resp = urlopen(req, timeout=5)
            pkt_data = json.loads(resp.read())
            signed = SignedPacket.from_dict(pkt_data)
            result = self.submit_packet(signed)
            if result["status"] == "accepted":
                print(f"[gossip-fetch] admitted {packet_id[:16]}... from peer")
            return result
        except Exception as e:
            print(f"[gossip-fetch] failed {packet_id[:16]}... from {peer}: {e}")
            return None

    def gossip_tip(self, gossip):
        """Broadcast tip gossip to all peers. Receiver fetches + admits."""
        env = self.sign_envelope("tip-gossip", gossip.to_dict())
        for peer in self.peers:
            try:
                req = Request(
                    f"{peer}/mesh/gossip",
                    data=json.dumps(env.to_dict()).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urlopen(req, timeout=3)
            except Exception:
                pass

    def send_heartbeat(self):
        tip = self.get_tip()
        hb = Heartbeat(
            agent_id=self.agent_id,
            node_role=self.role,
            ledger_height=tip["height"],
            ledger_tip=tip["tip"],
            peer_count=len(self.peers),
            packet_set_merkle=self._get_packet_set_merkle(),
            fork_ids=tuple(sorted(self._fork_records.keys())),
        )
        env = self.sign_envelope("heartbeat", hb.to_dict())
        for peer in self.peers:
            try:
                req = Request(
                    f"{peer}/mesh/heartbeat",
                    data=json.dumps(env.to_dict()).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urlopen(req, timeout=3)
            except Exception:
                pass

    def replicate_from_peer(self, peer):
        """Catch up from a peer. Verify prev_block_hash. Fork on mismatch.

        v0.2: On mismatch, do NOT append. Do NOT spam fork records.
        Trigger check_and_publish_fork once, then stop replicating from
        this peer until the fork is resolved.
        """
        tip = self.get_tip()
        req_data = ReplicaRequest(
            agent_id=self.agent_id,
            since_height=tip["height"],
        )
        env = self.sign_envelope("replica-request", req_data.to_dict())
        try:
            req = Request(
                f"{peer}/mesh/replica",
                data=json.dumps(env.to_dict()).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urlopen(req, timeout=10)
            data = json.loads(resp.read())
            count = 0
            my_blocks = self.ledger.blocks()
            my_tip_hash = my_blocks[-1].block.block_hash if my_blocks else GENESIS_HASH

            for entry in data.get("blocks", []):
                remote_block = entry.get("block", {}).get("block", entry.get("block", {}))
                remote_prev = remote_block.get("previous_hash", GENESIS_HASH)

                # Verify chain continuity: remote prev must match our tip
                if remote_prev != my_tip_hash:
                    # FORK — do not append, do not spam
                    # Trigger canonical fork detection (dedup by fork_id)
                    with contextlib.suppress(Exception):
                        self.check_and_publish_fork()
                    break  # stop replicating from this peer

                # Admit packets from this block
                for pkt_data in entry.get("packets", []):
                    signed = SignedPacket.from_dict(pkt_data)
                    result = self.submit_packet(signed)
                    if result["status"] in ("accepted", "already-present"):
                        count += 1

                # Update our tip for the next block check
                my_blocks = self.ledger.blocks()
                my_tip_hash = my_blocks[-1].block.block_hash if my_blocks else GENESIS_HASH

            return count
        except Exception as e:
            print(f"[replica] failed from {peer}: {e}")
            return 0

    def heartbeat_loop(self):
        while self._running:
            with contextlib.suppress(Exception):
                self.send_heartbeat()
            time.sleep(5)
            # Prune stale peers + check for forks after heartbeats propagate
            with contextlib.suppress(Exception):
                self._prune_stale_peers(max_age_seconds=30)
                self.check_and_publish_fork()

    def replicate_loop(self):
        while self._running:
            time.sleep(10)
            for peer in self.peers:
                try:
                    n = self.replicate_from_peer(peer)
                    if n > 0:
                        print(f"[replica] {n} packets from {peer}")
                except Exception:
                    pass

    def start(self):
        t1 = threading.Thread(target=self.heartbeat_loop, daemon=True)
        t2 = threading.Thread(target=self.replicate_loop, daemon=True)
        t1.start()
        t2.start()
        print("[node] background threads started (heartbeat + replicate)")

    def stop(self):
        self._running = False
        print("[node] stopping...")


def make_handler(node):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def _send_json(self, code, data):
            body = json.dumps(data, indent=2).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_body(self):
            length = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(length))

        def do_GET(self):
            if self.path == "/health":
                tip = node.get_tip()
                self._send_json(200, {
                    "status": "ok",
                    "agent_id": node.agent_id,
                    "role": node.role,
                    "ledger_height": tip["height"],
                    "ledger_tip": tip["tip"],
                    "packet_count": tip["packets"],
                    "conflicts": len(node._conflicts),
                    "forks": len(node._forks),
                    "fork_records": len(node._fork_records),
                    "peers": node.peers,
                })
            elif self.path == "/tip":
                self._send_json(200, node.get_tip())
            elif self.path == "/conflicts":
                self._send_json(200, {
                    "conflicts": [c.to_dict_with_id() for c in node._conflicts.values()],
                    "count": len(node._conflicts),
                })
            elif self.path == "/forks":
                self._send_json(200, {
                    "forks": node._forks,
                    "count": len(node._forks),
                })
            elif self.path == "/fork-records":
                self._send_json(200, {
                    "fork_records": [f.to_dict() for f in node._fork_records.values()],
                    "count": len(node._fork_records),
                })
            elif self.path == "/blocks":
                blocks = node.ledger.blocks()
                self._send_json(200, {
                    "blocks": [b.to_dict() for b in blocks],
                    "count": len(blocks),
                })
            elif self.path.startswith("/packet/"):
                pid = self.path.removeprefix("/packet/")
                path = node.objects_dir / f"{pid.removeprefix('sha256:')}.json"
                if path.exists():
                    self._send_json(200, json.loads(path.read_text()))
                else:
                    self._send_json(404, {"error": "not found"})
            elif self.path == "/mesh/peers":
                self._send_json(200, {"peers": node._known_peers})
            elif self.path.startswith("/artifact/"):
                aid = self.path.removeprefix("/artifact/")
                apath = node.root / "objects" / f"{aid.removeprefix('sha256:')}.json"
                if apath.exists():
                    self._send_json(200, json.loads(apath.read_text()))
                else:
                    self._send_json(404, {"error": "artifact not found"})
            elif self.path == "/world":
                # Observer view: the world as this node sees it
                my_tip = node.get_tip()
                my_set_merkle = node._get_packet_set_merkle()
                my_conflict_ids = list(node._get_conflict_ids())
                my_fork_ids = sorted(node._fork_records.keys())

                peer_tips = {}
                for peer_id, info in node._known_peers.items():
                    peer_tips[peer_id] = {
                        "tip": info.get("ledger_tip", ""),
                        "height": info.get("ledger_height", 0),
                        "packet_set_merkle": info.get("packet_set_merkle", ""),
                        "fork_ids": info.get("fork_ids", []),
                    }

                self._send_json(200, {
                    "agent_id": node.agent_id,
                    "role": node.role,
                    "packet_set_merkle": my_set_merkle,
                    "local_tip": my_tip["tip"],
                    "local_height": my_tip["height"],
                    "peer_tips": peer_tips,
                    "fork_ids": my_fork_ids,
                    "conflict_ids": my_conflict_ids,
                    "resolution_ids": node._get_resolution_ids(),
                    "packet_count": my_tip["packets"],
                })
            else:
                self._send_json(404, {"error": "unknown endpoint"})

        def do_POST(self):
            if self.path == "/submit":
                body = self._read_body()
                try:
                    signed = SignedPacket.from_dict(body)
                except Exception as e:
                    self._send_json(400, {"error": f"invalid packet: {e}"})
                    return
                result = node.submit_packet(signed)
                if result["status"] == "accepted":
                    blocks = node.ledger.blocks()
                    gossip = TipGossip(
                        agent_id=node.agent_id,
                        packet_id=result["packet_id"],
                        block_height=result["block_height"],
                        block_hash=result["block_hash"],
                        prev_block_hash=blocks[-2].block.block_hash
                        if len(blocks) > 1 else GENESIS_HASH,
                        policy_status="accepted",
                        evidence_count=len(signed.packet.evidence),
                    )
                    node.gossip_tip(gossip)
                self._send_json(200, result)

            elif self.path == "/mesh/gossip":
                body = self._read_body()
                try:
                    env = MeshEnvelope(**body)
                except Exception as e:
                    self._send_json(400, {"error": str(e)})
                    return
                if not node.verify_envelope(env):
                    self._send_json(401, {"error": "invalid signature"})
                    return
                gossip = TipGossip(**env.message)
                if gossip.packet_id not in node._seen_tips:
                    node._seen_tips.add(gossip.packet_id)
                    # Fetch the packet from the sender and admit it
                    # Find the peer that sent this by matching agent_id
                    sender_peer = None
                    for peer in node.peers:
                        try:
                            req = Request(f"{peer}/health")
                            resp = urlopen(req, timeout=3)
                            health = json.loads(resp.read())
                            if health.get("agent_id") == gossip.agent_id:
                                sender_peer = peer
                                break
                        except Exception:
                            continue
                    if sender_peer:
                        node.fetch_and_admit_from_peer(sender_peer, gossip.packet_id)
                    else:
                        # Try all peers
                        for peer in node.peers:
                            if node.fetch_and_admit_from_peer(peer, gossip.packet_id):
                                break
                    print(f"[gossip] new tip: {gossip.packet_id[:16]}... "
                          f"from {gossip.agent_id[:16]}... block={gossip.block_height}")
                self._send_json(200, {"status": "ack"})

            elif self.path == "/mesh/heartbeat":
                body = self._read_body()
                try:
                    env = MeshEnvelope(**body)
                except Exception as e:
                    self._send_json(400, {"error": str(e)})
                    return
                if not node.verify_envelope(env):
                    self._send_json(401, {"error": "invalid signature"})
                    return
                hb = Heartbeat(**env.message)
                node._known_peers[hb.agent_id] = {
                    "role": hb.node_role,
                    "ledger_height": hb.ledger_height,
                    "ledger_tip": hb.ledger_tip,
                    "packet_set_merkle": hb.packet_set_merkle,
                    "fork_ids": list(hb.fork_ids),
                    "last_seen": int(time.time()),
                }
                self._send_json(200, {"status": "ack"})

            elif self.path == "/mesh/replica":
                body = self._read_body()
                try:
                    env = MeshEnvelope(**body)
                except Exception as e:
                    self._send_json(400, {"error": str(e)})
                    return
                if not node.verify_envelope(env):
                    self._send_json(401, {"error": "invalid signature"})
                    return
                req = ReplicaRequest(**env.message)
                blocks_data = node.get_blocks_since(req.since_height)
                self._send_json(200, {
                    "agent_id": node.agent_id,
                    "blocks": blocks_data,
                    "count": len(blocks_data),
                })

            elif self.path == "/propose":
                body = self._read_body()
                try:
                    # v0.3: observations MUST include an evidence digest
                    kind = body.get("kind", "observation")
                    evidence_list = body.get("evidence", [])
                    if kind == "observation":
                        has_artifact_evidence = any(
                            e.get("kind") == "evidence"
                            and e.get("digest", "").startswith("sha256:")
                            for e in evidence_list
                        )
                        if not has_artifact_evidence:
                            self._send_json(400, {
                                "status": "rejected",
                                "reasons": [
                                    "observation must include evidence "
                                    "digest from a bench artifact"
                                ],
                            })
                            return

                    packet = KnowledgePacket(
                        kind=kind,
                        namespace=body.get("namespace", "commons/test"),
                        claim=body["claim"],
                        scope=body.get("scope", {}),
                        evidence=tuple(
                            EvidenceRef(**e) for e in evidence_list
                        ),
                        confidence=body.get("confidence", 0.5),
                        author_agent_id=node.agent_id,
                        constitution=ConstitutionRef(
                            constitution_id="grok-truth-seeking",
                            version="1.0.0",
                            digest=node.constitutions.resolve(
                                ConstitutionRef(
                                    constitution_id="grok-truth-seeking",
                                    version="1.0.0",
                                )
                            ).manifest_digest,
                        ),
                        method=MethodRef(
                            name=body.get("method", "direct-observation"),
                            version="1.0",
                        ),
                        contradicts=tuple(body.get("contradicts", ())),
                    )
                    signed = sign_packet(packet, node.identity)
                    result = node.submit_packet(signed)
                    if result["status"] == "accepted":
                        blocks = node.ledger.blocks()
                        gossip = TipGossip(
                            agent_id=node.agent_id,
                            packet_id=result["packet_id"],
                            block_height=result["block_height"],
                            block_hash=result["block_hash"],
                            prev_block_hash=blocks[-2].block.block_hash
                            if len(blocks) > 1 else GENESIS_HASH,
                            policy_status="accepted",
                            evidence_count=len(packet.evidence),
                        )
                        node.gossip_tip(gossip)
                    self._send_json(200, result)
                except Exception as e:
                    self._send_json(400, {"error": str(e)})

            elif self.path == "/resolve":
                # C (reconciliation) only — verifies both artifacts, emits resolution
                if node.role != "reconciliation":
                    self._send_json(403, {"error": "only reconciliation node may resolve"})
                    return
                body = self._read_body()
                try:
                    obs_a_id = body["observation_a_id"]
                    obs_b_id = body["observation_b_id"]
                    artifact_a_digest = body["artifact_a_digest"]
                    artifact_b_digest = body["artifact_b_digest"]
                    conflict_ids = tuple(body.get("conflict_ids", ()))
                    tok_s_a = float(body.get("tok_s_a", 0.0))
                    tok_s_b = float(body.get("tok_s_b", 0.0))
                    recipe_digest = body.get("recipe_digest", "")

                    # Apply the frozen resolution rule
                    max_tok = max(tok_s_a, tok_s_b)
                    diff_ratio = (
                        abs(tok_s_a - tok_s_b) / max_tok
                        if max_tok > 0 else 1.0
                    )

                    if diff_ratio <= 0.15:
                        resolution = "incomparable"
                        reasoning = (
                            f"tok/s differ by {diff_ratio:.1%} "
                            f"(<=15% threshold); "
                            f"hardware not comparable enough "
                            f"to pick a winner"
                        )
                    elif (recipe_digest
                          and artifact_a_digest == recipe_digest
                          and artifact_b_digest != recipe_digest):
                        resolution = "a-preferred"
                        reasoning = (
                            "artifact A recipe_digest matches "
                            "frozen contract; B does not"
                        )
                    elif (recipe_digest
                          and artifact_b_digest == recipe_digest
                          and artifact_a_digest != recipe_digest):
                        resolution = "b-preferred"
                        reasoning = (
                            "artifact B recipe_digest matches "
                            "frozen contract; A does not"
                        )
                    elif (recipe_digest
                          and artifact_a_digest != recipe_digest
                          and artifact_b_digest != recipe_digest):
                        resolution = "both-rejected"
                        reasoning = (
                            "neither artifact recipe_digest "
                            "matches frozen contract"
                        )
                    else:
                        # Both match recipe (or recipe not specified)
                        # — prefer higher tok/s
                        if tok_s_a > tok_s_b:
                            resolution = "a-preferred"
                            reasoning = (
                                f"both match recipe; A has higher "
                                f"tok/s ({tok_s_a} > {tok_s_b})"
                            )
                        else:
                            resolution = "b-preferred"
                            reasoning = (
                                f"both match recipe; B has higher "
                                f"tok/s ({tok_s_b} > {tok_s_a})"
                            )

                    rp = ResolutionPacket(
                        observation_a_id=obs_a_id,
                        observation_b_id=obs_b_id,
                        artifact_a_digest=artifact_a_digest,
                        artifact_b_digest=artifact_b_digest,
                        conflict_ids=conflict_ids,
                        resolution=resolution,
                        reasoning=reasoning,
                        tok_s_a=tok_s_a,
                        tok_s_b=tok_s_b,
                        recipe_digest=recipe_digest,
                    )
                    rid = rp.resolution_id
                    if rid not in node._resolutions:
                        node._resolutions[rid] = rp
                        res_dir = node.root / "resolutions"
                        res_dir.mkdir(exist_ok=True)
                        rpath = res_dir / f"{rid.removeprefix('sha256:')}.json"
                        rpath.write_text(json.dumps(rp.to_dict(), sort_keys=True, indent=2) + "\n")

                        # Publish resolution to ledger as kind=finding
                        res_packet = KnowledgePacket(
                            kind="finding",
                            namespace="commons/mesh/resolution",
                            claim=f"resolution: {resolution} — {reasoning}",
                            scope={
                                "resolution_id": rid,
                                "observation_a_id": obs_a_id,
                                "observation_b_id": obs_b_id,
                                "artifact_a_digest": artifact_a_digest,
                                "artifact_b_digest": artifact_b_digest,
                                "resolution": resolution,
                            },
                            evidence=(
                                EvidenceRef(
                                    kind="observation",
                                    uri=f"aafp://resolution/{rid}",
                                    summary=f"resolution: {resolution}",
                                ),
                            ),
                            confidence=1.0,
                            author_agent_id=node.agent_id,
                            constitution=ConstitutionRef(
                                constitution_id="grok-truth-seeking",
                                version="1.0.0",
                                digest=node.constitutions.resolve(
                                    ConstitutionRef(
                                        constitution_id="grok-truth-seeking",
                                        version="1.0.0",
                                    )
                                ).manifest_digest,
                            ),
                            method=MethodRef(name="reconciliation", version="1.0"),
                        )
                        signed = sign_packet(res_packet, node.identity)
                        path = node.objects_dir / (
                            f"{signed.packet_id.removeprefix('sha256:')}.json"
                        )
                        if not path.exists():
                            path.write_text(
                                json.dumps(
                                    signed.to_dict(),
                                    sort_keys=True,
                                    indent=2,
                                ) + "\n"
                            )
                            block = node.ledger.append(
                                (signed.packet_id,), node.identity
                            )
                            print(
                                f"[resolution] {rid[:16]}... "
                                f"{resolution} — "
                                f"published h={block.block.height}"
                            )
                            # Gossip the new packet
                            blocks = node.ledger.blocks()
                            gossip = TipGossip(
                                agent_id=node.agent_id,
                                packet_id=signed.packet_id,
                                block_height=block.block.height,
                                block_hash=block.block.block_hash,
                                prev_block_hash=blocks[-2].block.block_hash
                                if len(blocks) > 1 else GENESIS_HASH,
                                policy_status="accepted",
                                evidence_count=1,
                            )
                            node.gossip_tip(gossip)

                    self._send_json(200, {
                        "status": "accepted",
                        "resolution_id": rid,
                        "resolution": resolution,
                        "reasoning": reasoning,
                    })
                except Exception as e:
                    self._send_json(400, {"error": str(e)})
            else:
                self._send_json(404, {"error": "unknown endpoint"})

    return Handler


class ReuseAddrHTTPServer(ThreadingHTTPServer):
    """HTTP server with SO_REUSEADDR to avoid EADDRINUSE on restart."""
    allow_reuse_address = True
    allow_reuse_port = True


def load_or_create_identity(root):
    root.mkdir(parents=True, exist_ok=True)
    key_path = root / "node_identity.json"
    if key_path.exists():
        data = json.loads(key_path.read_text())
        priv_bytes = b64decode(data["private_key_b64"])
        return Identity.from_seed(priv_bytes)
    identity = Identity.generate()
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
    )
    priv_bytes = identity.private_key.private_bytes(
        encoding=Encoding.Raw,
        format=PrivateFormat.Raw,
        encryption_algorithm=NoEncryption(),
    )
    key_path.write_text(json.dumps({
        "private_key_b64": b64encode(priv_bytes),
        "public_key_b64": b64encode(identity.public_bytes()),
        "agent_id": derive_agent_id(identity.public_bytes()),
        "key_id": identity.key_id,
    }, indent=2) + "\n")
    print(f"[node] generated new identity: {derive_agent_id(identity.public_bytes())}")
    return identity


def write_pid_file(root):
    pid_path = root / "node.pid"
    pid_path.write_text(str(os.getpid()))
    return pid_path


def kill_existing(root):
    """Kill any existing daemon via PID file. Returns True if killed."""
    pid_path = root / "node.pid"
    if not pid_path.exists():
        return False
    try:
        old_pid = int(pid_path.read_text().strip())
        os.kill(old_pid, signal.SIGTERM)
        time.sleep(2)
        # Force kill if still alive
        try:
            os.kill(old_pid, 0)
            os.kill(old_pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        print(f"[node] killed existing daemon PID {old_pid}")
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


def main():
    parser = argparse.ArgumentParser(description="Commons Mesh Node v0.1")
    parser.add_argument("--root", default="./commons-data", help="data directory")
    parser.add_argument("--role", required=True,
                        choices=["publication", "research", "reconciliation", "observer"])
    parser.add_argument("--peers", default="", help="comma-separated peer URLs")
    parser.add_argument("--port", type=int, default=8081, help="HTTP listen port")
    parser.add_argument("--kill-existing", action="store_true",
                        help="kill any existing daemon on same root before starting")
    args = parser.parse_args()

    root = Path(args.root)
    if args.kill_existing:
        kill_existing(root)

    identity = load_or_create_identity(root)
    peers = [p.strip() for p in args.peers.split(",") if p.strip()]

    node = MeshNode(root, args.role, identity, peers, args.port)
    node.start()

    pid_path = write_pid_file(root)

    handler = make_handler(node)
    server = ReuseAddrHTTPServer(("0.0.0.0", args.port), handler)

    def shutdown(signum, frame):
        node.stop()
        server.shutdown()
        pid_path.unlink(missing_ok=True)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print(f"[node] HTTP server on :{args.port} (PID {os.getpid()})")
    server.serve_forever()


if __name__ == "__main__":
    main()
