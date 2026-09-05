"""Ed25519 identity, evidence, and signed receipts.

Reimplementation of the ``ironclad.trust`` surface consumed by
``aafp_commons``. Preserves the ``ironclad-ed25519-v1`` packet format
byte-for-byte:

- ``Identity`` — Ed25519 keypair with ``generate()``, ``from_seed()``,
  ``sign()``, ``public_bytes()``, and ``.key_id``.
- ``Evidence`` — frozen dataclass (predicate, subject, timestamp, data,
  observer, nonce) with ``digest()`` and ``signing_payload()``.
- ``Receipt`` — dataclass (evidence, signature_b64,
  previous_receipt_digest) with auto-computed ``receipt_digest``.
"""

from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ironclad.canon import canonical_cbor, content_digest


@dataclass(frozen=True)
class Identity:
    """Ed25519 signing identity.

    ``private_key`` is the only init field; ``public_key`` and ``key_id``
    are derived in ``__post_init__``.
    """

    private_key: Ed25519PrivateKey
    public_key: Any = field(init=False)
    key_id: str = field(init=False)

    def __post_init__(self) -> None:
        public = self.private_key.public_key()
        pub_bytes = public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        digest = content_digest(
            {"ed25519_pub_b64": base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode("ascii")}
        )
        object.__setattr__(self, "public_key", public)
        object.__setattr__(self, "key_id", digest)

    @classmethod
    def generate(cls) -> Identity:
        """Generate a fresh random Ed25519 identity."""
        return cls(private_key=Ed25519PrivateKey.generate())

    @classmethod
    def from_seed(cls, seed: bytes) -> Identity:
        """Derive a deterministic Ed25519 identity from a 32-byte seed."""
        if len(seed) != 32:
            raise ValueError("Ed25519 seed must be 32 bytes")
        return cls(private_key=Ed25519PrivateKey.from_private_bytes(seed))

    def sign(self, data: bytes) -> bytes:
        """Sign *data* with the Ed25519 private key."""
        return self.private_key.sign(data)

    def public_bytes(self) -> bytes:
        """Return the raw 32-byte public key."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )


@dataclass(frozen=True)
class Evidence:
    """A signed observation with a tamper-evident digest.

    The ``nonce`` field defaults to ``secrets.token_urlsafe(16)`` (22-char
    base64url). When reconstructing from a stored receipt, pass the stored
    nonce explicitly.
    """

    predicate: str
    subject: str
    timestamp: float
    data: dict[str, Any]
    observer: str
    nonce: str = field(default_factory=lambda: secrets.token_urlsafe(16))

    def digest(self) -> str:
        """Content-address all six fields."""
        return content_digest(
            {
                "predicate": self.predicate,
                "subject": self.subject,
                "timestamp": self.timestamp,
                "data": self.data,
                "observer": self.observer,
                "nonce": self.nonce,
            }
        )

    def signing_payload(self) -> bytes:
        """Return the canonical CBOR bytes that the receipt signature covers."""
        return canonical_cbor(
            {
                "digest": self.digest(),
                "predicate": self.predicate,
                "subject": self.subject,
            }
        )


@dataclass
class Receipt:
    """A signed, hash-chained receipt linking evidence into a tamper-evident trail.

    ``receipt_digest`` is auto-computed in ``__post_init__`` and excludes
    ``evidence.timestamp`` from the evidence sub-map.
    """

    evidence: Evidence
    signature_b64: str
    previous_receipt_digest: str | None
    receipt_digest: str = field(init=False)

    def __post_init__(self) -> None:
        d = content_digest(
            {
                "evidence": {
                    "predicate": self.evidence.predicate,
                    "subject": self.evidence.subject,
                    "data": self.evidence.data,
                    "observer": self.evidence.observer,
                    "nonce": self.evidence.nonce,
                },
                "signature_b64": self.signature_b64,
                "previous_receipt_digest": self.previous_receipt_digest,
            }
        )
        object.__setattr__(self, "receipt_digest", d)
