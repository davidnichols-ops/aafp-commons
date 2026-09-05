"""A deterministic, non-authoritative index for published research snapshots."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Protocol

from ironclad.canon import content_digest

from aafp_commons.constitutions import ConstitutionManifest
from aafp_commons.sharing import load_public_snapshot
from aafp_commons.signing import SignedPacket


class ResearchIndexBackend(Protocol):
    """Interface implemented by local or hosted public research indexes."""

    def ingest(self, snapshot: dict[str, Any]) -> int: ...

    def search(self, query: str, *, namespace: str | None = None,
               packet_kind: str | None = None, limit: int = 100) -> list[dict[str, Any]]: ...

    def stats(self) -> dict[str, int]: ...

    def checkpoint(self) -> dict[str, Any]: ...


class PublicResearchIndex:
    """Aggregate verified public packets without accepting private client state."""

    def __init__(self, *, max_packets: int = 100_000) -> None:
        if max_packets < 1:
            raise ValueError("max_packets must be positive")
        self.max_packets = max_packets
        self._packets: dict[str, dict[str, Any]] = {}
        self._constitutions: dict[tuple[str, str], dict[str, Any]] = {}

    def ingest(self, snapshot: dict[str, Any]) -> int:
        verified = load_public_snapshot(snapshot)
        if len(verified["packets"]) > self.max_packets:
            raise ValueError("snapshot exceeds index packet limit")
        decoded = [(SignedPacket.from_dict(packet).packet_id, packet)
                   for packet in verified["packets"]]
        new_ids = {packet_id for packet_id, _ in decoded if packet_id not in self._packets}
        if len(self) + len(new_ids) > self.max_packets:
            raise ValueError("index exceeds packet limit")
        for manifest in verified.get("constitutions", []):
            key = (manifest["constitution_id"], manifest["version"])
            self._constitutions.setdefault(key, manifest)
        added = 0
        for packet_id, packet in decoded:
            if packet_id not in self._packets:
                self._packets[packet_id] = packet
                added += 1
        return added

    def export_delta(self, packet_ids: list[str], *, max_packets: int = 100) -> dict[str, Any]:
        """Export a bounded, verified delta for packet IDs missing on a peer."""
        if max_packets < 1 or len(packet_ids) > max_packets:
            raise ValueError("delta exceeds packet limit")
        if any(not isinstance(item, str) for item in packet_ids):
            raise ValueError("delta packet_ids must be strings")
        packets = [deepcopy(self._packets[item]) for item in sorted(set(packet_ids))
                   if item in self._packets]
        manifests = []
        for packet in packets:
            ref = packet["packet"]["constitution"]
            key = (ref["constitution_id"], ref["version"])
            if key in self._constitutions and self._constitutions[key] not in manifests:
                manifests.append(deepcopy(self._constitutions[key]))
        return {"schema": "aafp.commons/research-delta@1", "packets": packets,
                "constitutions": manifests, "count": len(packets)}

    def apply_delta(self, delta: dict[str, Any]) -> int:
        """Verify and idempotently apply a peer delta."""
        if delta.get("schema") != "aafp.commons/research-delta@1":
            raise ValueError("unsupported research delta schema")
        snapshot = {**delta, "schema": "aafp.commons/research-snapshot@1"}
        return self.ingest(snapshot)

    def search(
        self, query: str, *, namespace: str | None = None,
        packet_kind: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        needle = query.casefold().strip()
        if not needle:
            return []
        return [deepcopy(p) for p in self._packets.values()
                if needle in (p["packet"].get("claim", "") + " " +
                              p["packet"].get("namespace", "")).casefold()
                and (namespace is None or p["packet"].get("namespace", "").startswith(namespace))
                and (packet_kind is None or p["packet"].get("kind") == packet_kind)][:limit]

    def save(self, path: str | Path) -> None:
        """Persist the verified index as a portable snapshot-like document."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        value = {"schema": "aafp.commons/research-index@1",
                 "packets": list(self._packets.values()), "count": len(self),
                 "max_packets": self.max_packets,
                 "constitutions": list(self._constitutions.values())}
        target.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> PublicResearchIndex:
        """Load a persisted index, rechecking every packet signature."""
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if value.get("schema") != "aafp.commons/research-index@1":
            raise ValueError("unsupported research index schema")
        packets = value.get("packets", [])
        if value.get("count") != len(packets):
            raise ValueError("research index count is invalid")
        index = cls(max_packets=value.get("max_packets", 100_000))
        constitutions = value.get("constitutions", [])
        if not isinstance(constitutions, list):
            raise ValueError("research index constitutions must be an array")
        validated_constitutions = [ConstitutionManifest.from_dict(item).to_dict()
                                   for item in constitutions]
        index.ingest({"schema": "aafp.commons/research-snapshot@1",
                      "packets": packets, "constitutions": validated_constitutions,
                      "count": len(packets)})
        return index

    def __len__(self) -> int:
        return len(self._packets)

    def get_constitution(self, constitution_id: str, version: str) -> dict[str, Any] | None:
        """Return immutable manifest metadata retained for an indexed packet."""
        value = self._constitutions.get((constitution_id, version))
        return deepcopy(value) if value is not None else None

    def list_constitutions(self) -> list[dict[str, Any]]:
        """List retained manifests in stable ID/version order."""
        return [deepcopy(self._constitutions[key]) for key in sorted(self._constitutions)]

    def stats(self) -> dict[str, int]:
        """Return non-sensitive size and capacity metrics for health checks."""
        return {
            "packet_count": len(self._packets),
            "constitution_count": len(self._constitutions),
            "max_packets": self.max_packets,
        }

    def checkpoint(self) -> dict[str, Any]:
        """Return a deterministic state comparison point for replication."""
        packet_ids = sorted(self._packets)
        constitution_ids = sorted(f"{key[0]}@{key[1]}" for key in self._constitutions)
        return {
            "schema": "aafp.commons/research-checkpoint@1",
            "packet_count": len(packet_ids),
            "constitution_count": len(constitution_ids),
            "packet_ids": packet_ids,
            "constitution_ids": constitution_ids,
            "digest": content_digest({"packets": packet_ids, "constitutions": constitution_ids}),
        }

    def missing_from_checkpoint(self, checkpoint: dict[str, Any]) -> list[str]:
        """Return packet IDs advertised by a peer that this index lacks."""
        if checkpoint.get("schema") != "aafp.commons/research-checkpoint@1":
            raise ValueError("unsupported research checkpoint schema")
        packet_ids = checkpoint.get("packet_ids")
        if (not isinstance(packet_ids, list)
                or any(not isinstance(item, str) for item in packet_ids)):
            raise ValueError("checkpoint packet_ids must be an array of strings")
        constitution_ids = checkpoint.get("constitution_ids")
        if (not isinstance(constitution_ids, list)
                or any(not isinstance(item, str) for item in constitution_ids)):
            raise ValueError("checkpoint constitution_ids must be an array of strings")
        if checkpoint.get("packet_count") != len(packet_ids):
            raise ValueError("checkpoint packet count is invalid")
        if checkpoint.get("constitution_count") != len(constitution_ids):
            raise ValueError("checkpoint constitution count is invalid")
        expected = content_digest({"packets": sorted(packet_ids),
                                   "constitutions": sorted(constitution_ids)})
        if checkpoint.get("digest") != expected:
            raise ValueError("checkpoint digest is invalid")
        return sorted(set(packet_ids) - self._packets.keys())
