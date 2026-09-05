"""Signed append-only audit ledger for accepted packet content addresses.

This is a verifiable hash chain with Merkle commitments and authority
signatures. It intentionally does not claim decentralized consensus.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from ironclad.canon import content_digest
from ironclad.trust import Identity

from aafp_commons.canonical import b64decode, b64encode, canonical_json, digest

BLOCK_DOMAIN = b"aafp-commons/ledger-block/v1\x00"
GENESIS_HASH = "sha256:" + "0" * 64


def merkle_root(items: Iterable[str]) -> str:
    level = list(items)
    if not level:
        return digest([])
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [digest({"left": level[i], "right": level[i + 1]}) for i in range(0, len(level), 2)]
    return level[0]


def _signer_key_id(public_key: bytes) -> str:
    return cast(str, content_digest({"ed25519_pub_b64": b64encode(public_key)}))


@dataclass(frozen=True)
class LedgerBlock:
    height: int
    previous_hash: str
    packet_digests: tuple[str, ...]
    merkle_root: str
    authority_key_id: str
    timestamp: int
    schema: str = "aafp.commons/ledger-block@1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> LedgerBlock:
        data = dict(value)
        data["packet_digests"] = tuple(data["packet_digests"])
        return cls(**data)

    @property
    def block_hash(self) -> str:
        return digest(self.to_dict())


@dataclass(frozen=True)
class SignedBlock:
    block: LedgerBlock
    authority_public_key_b64: str
    signature_b64: str
    scheme: str = "ironclad-ed25519-v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "scheme": self.scheme,
            "block": self.block.to_dict(),
            "block_hash": self.block.block_hash,
            "authority_public_key_b64": self.authority_public_key_b64,
            "signature_b64": self.signature_b64,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SignedBlock:
        block = LedgerBlock.from_dict(value["block"])
        if value.get("block_hash") != block.block_hash:
            raise ValueError("ledger block content address mismatch")
        return cls(
            block=block,
            authority_public_key_b64=value["authority_public_key_b64"],
            signature_b64=value["signature_b64"],
            scheme=value.get("scheme", "ironclad-ed25519-v1"),
        )

    def verify(self) -> bool:
        try:
            public_bytes = b64decode(self.authority_public_key_b64)
            if _signer_key_id(public_bytes) != self.block.authority_key_id:
                return False
            if merkle_root(self.block.packet_digests) != self.block.merkle_root:
                return False
            Ed25519PublicKey.from_public_bytes(public_bytes).verify(
                b64decode(self.signature_b64),
                BLOCK_DOMAIN + canonical_json(self.block.to_dict()),
            )
            return True
        except Exception:
            return False


@dataclass(frozen=True)
class LedgerVerification:
    valid: bool
    blocks: int
    packets: int
    errors: tuple[str, ...]


class Ledger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def blocks(self) -> list[SignedBlock]:
        if not self.path.exists():
            return []
        blocks: list[SignedBlock] = []
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                blocks.append(SignedBlock.from_dict(json.loads(line)))
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
                raise ValueError(f"invalid ledger line {number}: {error}") from error
        return blocks

    def append(self, packet_digests: Iterable[str], authority: Identity) -> SignedBlock:
        items = tuple(packet_digests)
        if not items:
            raise ValueError("cannot append an empty block")
        existing = self.blocks()
        block = LedgerBlock(
            height=len(existing),
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

    def verify(self) -> LedgerVerification:
        errors: list[str] = []
        try:
            blocks = self.blocks()
        except ValueError as error:
            return LedgerVerification(False, 0, 0, (str(error),))
        previous = GENESIS_HASH
        packet_count = 0
        for expected_height, signed in enumerate(blocks):
            block = signed.block
            if block.height != expected_height:
                errors.append(f"block {expected_height}: height is {block.height}")
            if block.previous_hash != previous:
                errors.append(f"block {expected_height}: previous hash mismatch")
            if not signed.verify():
                errors.append(f"block {expected_height}: signature or Merkle root invalid")
            previous = block.block_hash
            packet_count += len(block.packet_digests)
        return LedgerVerification(not errors, len(blocks), packet_count, tuple(errors))
