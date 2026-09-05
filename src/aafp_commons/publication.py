"""Authenticated publication boundary for verified public research snapshots."""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any, Protocol

from ironclad.canon import content_digest
from ironclad.trust import Identity

from aafp_commons.index import PublicResearchIndex
from aafp_commons.sharing import load_public_snapshot

PUBLICATION_SCHEMA = "aafp.commons/research-publication@1"
PUBLICATION_STATE_SCHEMA = "aafp.commons/publication-state@1"


class PublicationBackend(Protocol):
    """Agent-facing contract shared by local and hosted publishers."""

    def publish(
        self, snapshot: dict[str, Any], publisher: Identity, **kwargs: Any
    ) -> dict[str, Any]: ...

    def search(self, query: str, **filters: Any) -> list[dict[str, Any]]: ...

    def stats(self) -> dict[str, int]: ...

    def checkpoint(self) -> dict[str, Any]: ...

    def publications(self, *, limit: int = 100) -> list[dict[str, Any]]: ...

    def revoke_publisher(self, publisher_id: str) -> None: ...


class PublicationService:
    """Small authenticated publication service backed by a public index.

    Packet signer identity remains inside each signed packet. ``publisher_id``
    records the agent that submitted the snapshot and is deliberately separate.
    """

    def __init__(self, index: PublicResearchIndex | None = None,
                 *, max_publications_per_publisher: int = 100) -> None:
        if max_publications_per_publisher < 1:
            raise ValueError("max_publications_per_publisher must be positive")
        self.index = index or PublicResearchIndex()
        self.max_publications_per_publisher = max_publications_per_publisher
        self._publications: dict[str, dict[str, Any]] = {}
        self._publisher_counts: dict[str, int] = {}
        self._revoked_publishers: set[str] = set()

    def revoke_publisher(self, publisher_id: str) -> None:
        """Reject future publications from a publisher key id."""
        if not publisher_id.strip():
            raise ValueError("publisher_id must not be empty")
        self._revoked_publishers.add(publisher_id)

    def is_publisher_revoked(self, publisher_id: str) -> bool:
        """Return whether a publisher key is currently revoked."""
        return publisher_id in self._revoked_publishers

    def save(self, directory: str | Path) -> None:
        """Persist index and publisher lifecycle state for safe restart."""
        root = Path(directory)
        root.mkdir(parents=True, exist_ok=True)
        self.index.save(root / "index.json")
        state = {"schema": PUBLICATION_STATE_SCHEMA,
                 "max_publications_per_publisher": self.max_publications_per_publisher,
                 "revoked_publishers": sorted(self._revoked_publishers),
                 "publisher_counts": self._publisher_counts,
                 "publications": self.publications(limit=max(1, len(self._publications)))}
        (root / "service.json").write_text(json.dumps(state, sort_keys=True, indent=2) + "\n",
                                            encoding="utf-8")

    @classmethod
    def load(cls, directory: str | Path) -> PublicationService:
        root = Path(directory)
        state = json.loads((root / "service.json").read_text(encoding="utf-8"))
        if state.get("schema") != PUBLICATION_STATE_SCHEMA:
            raise ValueError("unsupported publication state schema")
        revoked = state.get("revoked_publishers", [])
        counts = state.get("publisher_counts", {})
        publications = state.get("publications", [])
        if (not isinstance(revoked, list) or any(not isinstance(item, str) for item in revoked)
                or not isinstance(counts, dict) or not isinstance(publications, list)):
            raise ValueError("publication state fields are invalid")
        max_per_publisher = state.get("max_publications_per_publisher")
        if (not isinstance(max_per_publisher, int) or max_per_publisher < 1
                or any(not isinstance(key, str) or not isinstance(value, int)
                       or value < 0 or value > max_per_publisher
                       for key, value in counts.items())):
            raise ValueError("publication state counters are invalid")
        if (any(not isinstance(item, dict) or item.get("schema") != PUBLICATION_SCHEMA
                for item in publications)):
            raise ValueError("publication state records are invalid")
        observed: dict[str, int] = {}
        for item in publications:
            publisher_id = item.get("publisher_id")
            if not isinstance(publisher_id, str):
                raise ValueError("publication state records are invalid")
            observed[publisher_id] = observed.get(publisher_id, 0) + 1
        publication_ids = [item.get("publication_id") for item in publications]
        if (any(not isinstance(item, str) for item in publication_ids)
                or len(set(publication_ids)) != len(publication_ids)):
            raise ValueError("publication state records are invalid")
        if observed != counts:
            raise ValueError("publication state counters do not match records")
        service = cls(PublicResearchIndex.load(root / "index.json"),
                      max_publications_per_publisher=max_per_publisher)
        service._revoked_publishers = set(revoked)
        service._publisher_counts = dict(counts)
        service._publications = {item["publication_id"]: item for item in publications}
        return service

    def publish(
        self,
        snapshot: dict[str, Any],
        publisher: Identity,
        authorize: Callable[[Identity, dict[str, Any]], bool] | None = None,
        privacy_policy: Callable[[dict[str, Any]], bool] | None = None,
    ) -> dict[str, Any]:
        verified = load_public_snapshot(snapshot)
        publisher_id = publisher.key_id
        if publisher_id in self._revoked_publishers:
            raise PermissionError("publisher has been revoked")
        if self._publisher_counts.get(publisher_id, 0) >= self.max_publications_per_publisher:
            raise PermissionError("publisher publication limit exceeded")
        if authorize is not None and not authorize(publisher, verified):
            raise PermissionError("publisher is not authorized")
        if privacy_policy is not None:
            for packet in verified["packets"]:
                if not privacy_policy(packet):
                    raise PermissionError("snapshot failed privacy policy")
        publication_id = content_digest({
            "snapshot": verified,
            "publisher_id": publisher_id,
        })
        added = self.index.ingest(verified)
        record = {
            "schema": PUBLICATION_SCHEMA,
            "publication_id": publication_id,
            "publisher_id": publisher_id,
            "published_at": int(time.time()),
            "packet_count": len(verified["packets"]),
            "added_packets": added,
        }
        self._publications[publication_id] = record
        self._publisher_counts[publisher_id] = self._publisher_counts.get(publisher_id, 0) + 1
        return deepcopy(record)

    def publications(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return a bounded, deterministic publication history."""
        if limit < 1:
            raise ValueError("limit must be positive")
        return deepcopy([self._publications[key] for key in sorted(self._publications)][:limit])

    def search(self, query: str, **filters: Any) -> list[dict[str, Any]]:
        return self.index.search(query, **filters)

    def stats(self) -> dict[str, int]:
        return {
            **self.index.stats(),
            "publications": len(self._publications),
            "revoked_publishers": len(self._revoked_publishers),
        }

    def checkpoint(self) -> dict[str, Any]:
        """Expose the underlying index checkpoint for replication clients."""
        return self.index.checkpoint()

    def missing_from_checkpoint(self, checkpoint: dict[str, Any]) -> list[str]:
        """Report packet IDs advertised by a peer but absent locally."""
        return self.index.missing_from_checkpoint(checkpoint)

    def sync_from_peer(
        self,
        checkpoint: dict[str, Any],
        fetch_delta: Callable[[list[str]], dict[str, Any]],
    ) -> int:
        """Fetch and verify one bounded delta from a peer."""
        missing = self.missing_from_checkpoint(checkpoint)
        if not missing:
            return 0
        delta = fetch_delta(missing)
        return self.index.apply_delta(delta)
