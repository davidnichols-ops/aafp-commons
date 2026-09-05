"""Local content-addressed commons node."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ironclad.trust import Identity

from aafp_commons.adoption import (
    AdoptionRequestError,
    ConstitutionAdoptionDecision,
    ConstitutionAdoptionRequest,
    FileAdoptionDecisionStore,
    FileAdoptionRequestStore,
)
from aafp_commons.constitutions import (
    ConstitutionError,
    ConstitutionManifest,
    ConstitutionResolver,
    FileConstitutionResolver,
)
from aafp_commons.handshake import FileHandshakeStore, RuntimeHandshake
from aafp_commons.ledger import Ledger, LedgerVerification
from aafp_commons.models import ConstitutionRef
from aafp_commons.policy import AdmissionPolicy, PolicyDecision
from aafp_commons.signing import SignedPacket


@dataclass(frozen=True)
class RepositoryVerification:
    valid: bool
    objects: int
    ledger: LedgerVerification
    errors: tuple[str, ...]


class CommonsRepository:
    def __init__(
        self,
        root: str | Path,
        policy: AdmissionPolicy | None = None,
        constitution_resolver: ConstitutionResolver | None = None,
    ) -> None:
        self.root = Path(root)
        self.objects_dir = self.root / "objects"
        self.ledger = Ledger(self.root / "ledger.jsonl")
        self.policy = policy or AdmissionPolicy()
        self.constitutions = constitution_resolver or FileConstitutionResolver(
            self.root / "constitutions"
        )
        self.adoption_requests = FileAdoptionRequestStore(self.root / "adoption-requests")
        self.adoption_decisions = FileAdoptionDecisionStore(self.root / "adoption-decisions")
        self.runtime_handshakes = FileHandshakeStore(self.root / "runtime-handshakes")

    def initialize(self) -> None:
        self.objects_dir.mkdir(parents=True, exist_ok=True)
        metadata = self.root / "commons.json"
        if not metadata.exists():
            metadata.write_text(
                json.dumps(
                    {
                        "schema": "aafp.commons/repository@1",
                        "ledger": "ledger.jsonl",
                        "constitutions": "constitutions",
                        "adoption_requests": "adoption-requests",
                        "adoption_decisions": "adoption-decisions",
                        "runtime_handshakes": "runtime-handshakes",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

    def object_path(self, packet_id: str) -> Path:
        if not packet_id.startswith("sha256:"):
            raise ValueError("packet id must be a sha256 content address")
        return self.objects_dir / f"{packet_id.removeprefix('sha256:')}.json"

    def submit(self, signed: SignedPacket, authority: Identity) -> PolicyDecision:
        try:
            constitution = self.constitutions.resolve(signed.packet.constitution)
        except ConstitutionError as error:
            return PolicyDecision(False, "rejected", (str(error),))
        decision = self.policy.evaluate(signed, constitution)
        if not decision.accepted:
            return decision
        self.initialize()
        path = self.object_path(signed.packet_id)
        encoded = json.dumps(signed.to_dict(), sort_keys=True, indent=2) + "\n"
        if path.exists():
            existing = SignedPacket.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if existing.to_dict() != signed.to_dict():
                raise ValueError("content-address collision or attempted mutation")
            return PolicyDecision(True, "already-present", ())
        path.write_text(encoded, encoding="utf-8")
        self.ledger.append((signed.packet_id,), authority)
        return decision

    def install_constitution(self, manifest: ConstitutionManifest) -> ConstitutionRef:
        """Install a manifest without treating its contents as an authority grant."""

        if not isinstance(self.constitutions, FileConstitutionResolver):
            raise TypeError("the configured constitution resolver does not support installation")
        return self.constitutions.install(manifest)

    def record_adoption_request(self, request: ConstitutionAdoptionRequest) -> str:
        """Store an exact preference request without granting any authority."""
        return self.adoption_requests.record(request, self.constitutions)

    def respond_to_adoption_request(
        self,
        request_id: str,
        *,
        accepted: bool,
        reason: str = "",
        decided_at: int | None = None,
    ) -> ConstitutionAdoptionDecision:
        """Record a local runtime response without changing authority or policy."""
        request = self.adoption_requests.get(request_id)
        self.constitutions.resolve(request.constitution)
        decision_kwargs: dict[str, object] = {
            "request_id": request.request_id,
            "constitution": request.constitution,
            "runtime": request.runtime,
            "accepted": accepted,
            "reason": reason,
        }
        if decided_at is not None:
            decision_kwargs["decided_at"] = decided_at
        decision = ConstitutionAdoptionDecision(**decision_kwargs)  # type: ignore[arg-type]
        self.adoption_decisions.record(decision)
        return decision

    def resolve_adopted_constitution(self, request_id: str) -> ConstitutionManifest:
        """Resolve guidance only after the local runtime accepted the request."""
        request = self.adoption_requests.get(request_id)
        decision = self.adoption_decisions.get(request_id)
        if not decision.accepted:
            raise AdoptionRequestError("the runtime rejected this adoption request")
        if (
            decision.constitution != request.constitution
            or decision.runtime != request.runtime
        ):
            raise AdoptionRequestError("adoption decision does not match its request")
        return self.constitutions.resolve(request.constitution)

    def record_runtime_handshake(self, handshake: RuntimeHandshake) -> str:
        """Store runtime discovery metadata without granting any authority."""
        return self.runtime_handshakes.record(handshake)

    def get(self, packet_id: str) -> SignedPacket:
        return SignedPacket.from_dict(
            json.loads(self.object_path(packet_id).read_text(encoding="utf-8"))
        )

    def query(self, namespace_prefix: str = "commons/") -> list[SignedPacket]:
        if not self.objects_dir.exists():
            return []
        packets = []
        for path in sorted(self.objects_dir.glob("*.json")):
            signed = SignedPacket.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if signed.packet.namespace.startswith(namespace_prefix):
                packets.append(signed)
        return packets

    def verify(self) -> RepositoryVerification:
        errors: list[str] = []
        object_ids: set[str] = set()
        if self.objects_dir.exists():
            for path in sorted(self.objects_dir.glob("*.json")):
                try:
                    signed = SignedPacket.from_dict(json.loads(path.read_text(encoding="utf-8")))
                    if not signed.verify():
                        errors.append(f"{path.name}: invalid packet signature or receipt")
                    if path.stem != signed.packet_id.removeprefix("sha256:"):
                        errors.append(
                            f"{path.name}: filename does not match packet content address"
                        )
                    try:
                        constitution = self.constitutions.resolve(signed.packet.constitution)
                        if signed.packet.constitution.digest is None:
                            errors.append(
                                f"{path.name}: constitution reference is not digest-pinned"
                            )
                        errors.extend(
                            f"{path.name}: {reason}"
                            for reason in constitution.validate_packet(signed.packet)
                        )
                    except ConstitutionError as error:
                        errors.append(f"{path.name}: {error}")
                    object_ids.add(signed.packet_id)
                except Exception as error:
                    errors.append(f"{path.name}: {error}")
        ledger_result = self.ledger.verify()
        try:
            referenced = {
                packet_id
                for signed_block in self.ledger.blocks()
                for packet_id in signed_block.block.packet_digests
            }
            for missing in sorted(referenced - object_ids):
                errors.append(f"ledger references missing object {missing}")
            for uncommitted in sorted(object_ids - referenced):
                errors.append(f"object is not committed to ledger {uncommitted}")
        except ValueError:
            pass
        return RepositoryVerification(
            valid=ledger_result.valid and not errors,
            objects=len(object_ids),
            ledger=ledger_result,
            errors=tuple(errors) + ledger_result.errors,
        )
