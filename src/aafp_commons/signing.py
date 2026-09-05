"""Ironclad-backed signing for immutable knowledge packets."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from ironclad.canon import content_digest
from ironclad.trust import Evidence, Identity, Receipt

from aafp_commons.canonical import b64decode, b64encode, canonical_json
from aafp_commons.models import KnowledgePacket

PACKET_DOMAIN = b"aafp-commons/knowledge-packet/v1\x00"


def _signer_key_id(public_key: bytes) -> str:
    return cast(str, content_digest({"ed25519_pub_b64": b64encode(public_key)}))


@dataclass(frozen=True)
class SignedPacket:
    packet: KnowledgePacket
    signer_key_id: str
    signer_public_key_b64: str
    signature_b64: str
    signed_at: int
    receipt: dict[str, Any]
    scheme: str = "ironclad-ed25519-v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "scheme": self.scheme,
            "packet": self.packet.to_dict(),
            "signer_key_id": self.signer_key_id,
            "signer_public_key_b64": self.signer_public_key_b64,
            "signature_b64": self.signature_b64,
            "signed_at": self.signed_at,
            "receipt": self.receipt,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SignedPacket:
        return cls(
            packet=KnowledgePacket.from_dict(value["packet"]),
            signer_key_id=value["signer_key_id"],
            signer_public_key_b64=value["signer_public_key_b64"],
            signature_b64=value["signature_b64"],
            signed_at=value["signed_at"],
            receipt=value["receipt"],
            scheme=value.get("scheme", "ironclad-ed25519-v1"),
        )

    @property
    def packet_id(self) -> str:
        return self.packet.packet_id

    def verify(self) -> bool:
        try:
            public_bytes = b64decode(self.signer_public_key_b64)
            if _signer_key_id(public_bytes) != self.signer_key_id:
                return False
            public_key = Ed25519PublicKey.from_public_bytes(public_bytes)
            payload = PACKET_DOMAIN + canonical_json(self.packet.to_dict())
            public_key.verify(b64decode(self.signature_b64), payload)

            evidence_data = self.receipt["evidence"]
            evidence = Evidence(**evidence_data)
            if evidence.subject != self.packet_id:
                return False
            if evidence.observer != self.signer_key_id:
                return False
            public_key.verify(b64decode(self.receipt["signature_b64"]), evidence.signing_payload())
            rebuilt = Receipt(
                evidence=evidence,
                signature_b64=self.receipt["signature_b64"],
                previous_receipt_digest=self.receipt.get("previous_receipt_digest"),
            )
            return cast(bool, rebuilt.receipt_digest == self.receipt["receipt_digest"])
        except (KeyError, TypeError, ValueError):
            return False
        except Exception:  # cryptographic verification fails closed
            return False


def sign_packet(
    packet: KnowledgePacket,
    identity: Identity,
    previous_receipt_digest: str | None = None,
) -> SignedPacket:
    payload = PACKET_DOMAIN + canonical_json(packet.to_dict())
    signature = identity.sign(payload)
    evidence = Evidence(
        predicate="aafp.commons:packet:signed",
        subject=packet.packet_id,
        timestamp=time.time(),
        data={
            "schema": packet.schema,
            "namespace": packet.namespace,
            "author_agent_id": packet.author_agent_id,
        },
        observer=identity.key_id,
    )
    receipt_signature = b64encode(identity.sign(evidence.signing_payload()))
    receipt = Receipt(
        evidence=evidence,
        signature_b64=receipt_signature,
        previous_receipt_digest=previous_receipt_digest,
    )
    return SignedPacket(
        packet=packet,
        signer_key_id=identity.key_id,
        signer_public_key_b64=b64encode(identity.public_bytes()),
        signature_b64=b64encode(signature),
        signed_at=int(time.time()),
        receipt={
            "evidence": {
                "predicate": evidence.predicate,
                "subject": evidence.subject,
                "timestamp": evidence.timestamp,
                "data": evidence.data,
                "observer": evidence.observer,
                "nonce": evidence.nonce,
            },
            "signature_b64": receipt.signature_b64,
            "previous_receipt_digest": receipt.previous_receipt_digest,
            "receipt_digest": receipt.receipt_digest,
        },
    )
