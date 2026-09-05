"""Explicit, portable export of public research packets."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ironclad.trust import Identity

from aafp_commons.constitutions import ConstitutionManifest
from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import SignedPacket

SNAPSHOT_SCHEMA = "aafp.commons/research-snapshot@1"


def export_public_snapshot(repository: CommonsRepository, output: str | Path) -> dict[str, Any]:
    """Write a deterministic snapshot containing only public packets."""
    # An explicit empty prefix includes all namespaces; visibility remains the
    # publication boundary, so private and organization-scoped packets stay out.
    packets = [item for item in repository.query("") if item.packet.visibility == "public"]
    manifests = []
    seen: set[tuple[str, str]] = set()
    for item in packets:
        ref = item.packet.constitution
        key = (ref.constitution_id, ref.version)
        if key not in seen:
            manifests.append(repository.constitutions.resolve(ref).to_dict())
            seen.add(key)
    snapshot = {"schema": SNAPSHOT_SCHEMA, "packets": [p.to_dict() for p in packets],
                "constitutions": manifests, "count": len(packets)}
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return snapshot


def import_public_snapshot(
    repository: CommonsRepository, snapshot: dict[str, Any], authority: Identity
) -> int:
    """Validate and admit a public snapshot through the recipient's policy gates."""
    if snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise ValueError("unsupported research snapshot schema")
    constitutions = snapshot.get("constitutions")
    packets = snapshot.get("packets")
    if not isinstance(constitutions, list) or not isinstance(packets, list):
        raise ValueError("snapshot constitutions and packets must be arrays")
    if snapshot.get("count") != len(packets):
        raise ValueError("snapshot count does not match packets")
    # Validate the complete payload before installing anything, preventing a
    # malformed later packet from leaving partially imported state.
    decoded_packets = []
    for value in packets:
        signed = SignedPacket.from_dict(value)
        if signed.packet.visibility != "public" or not signed.verify():
            raise ValueError("snapshot contains a non-public or invalid signed packet")
        decoded_packets.append(signed)
    decoded_constitutions = [ConstitutionManifest.from_dict(value) for value in constitutions]
    for manifest in decoded_constitutions:
        repository.install_constitution(manifest)
    accepted = 0
    for signed in decoded_packets:
        decision = repository.submit(signed, authority)
        if not decision.accepted:
            raise ValueError("snapshot packet rejected: " + "; ".join(decision.reasons))
        accepted += 1
    return accepted


def load_public_snapshot(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    """Load and verify a portable snapshot without mutating a repository."""
    snapshot = (json.loads(Path(source).read_text(encoding="utf-8"))
                if isinstance(source, (str, Path)) else dict(source))
    if snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise ValueError("unsupported research snapshot schema")
    packets = snapshot.get("packets")
    if not isinstance(packets, list) or snapshot.get("count") != len(packets):
        raise ValueError("snapshot packet count is invalid")
    for value in packets:
        signed = SignedPacket.from_dict(value)
        if signed.packet.visibility != "public" or not signed.verify():
            raise ValueError("snapshot contains an invalid public packet")
    return snapshot


def search_public_snapshot(
    snapshot: dict[str, Any], query: str, *, namespace: str | None = None,
    packet_kind: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    """Search claims, namespaces, and evidence summaries in a verified snapshot."""
    verified = load_public_snapshot(snapshot)
    needle = query.casefold().strip()
    if limit < 1:
        raise ValueError("limit must be positive")
    if not needle:
        return []
    matches = []
    for value in verified["packets"]:
        packet = value["packet"]
        haystack = " ".join((packet.get("claim", ""), packet.get("namespace", ""),
                             json.dumps(packet.get("evidence", []), sort_keys=True))).casefold()
        if (needle in haystack and
                (namespace is None or packet["namespace"].startswith(namespace)) and
                (packet_kind is None or packet["kind"] == packet_kind)):
            matches.append(value)
    return matches[:limit]
