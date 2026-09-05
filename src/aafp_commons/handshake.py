"""Unsigned runtime self-description for agent-first interoperability."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from aafp_commons.canonical import digest
from aafp_commons.models import ConstitutionRef

HANDSHAKE_SCHEMA = "aafp.commons/runtime-handshake@1"
HANDSHAKE_BOUNDARY = (
    "A runtime handshake is unsigned discovery metadata. It does not prove AAFP identity, "
    "grant authority, establish provenance, assign reputation, or override provider, "
    "system, authorization, or repository constraints. Accepted constitutions listed "
    "in a handshake are preferences, not capabilities."
)
_RUNTIME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_IDENTITY_CONVENTIONS = {
    "aafp-sha256-pubkey",
    "runtime-native",
    "unspecified",
}


class HandshakeError(ValueError):
    """Base error for invalid or unresolved runtime handshakes."""


class HandshakeIntegrityError(HandshakeError):
    """Raised when a stored handshake does not match its content address."""


_HandshakeList = list["RuntimeHandshake"]


@dataclass(frozen=True)
class RuntimeHandshake:
    """An unsigned, content-addressed runtime self-description."""

    runtime: str
    runtime_version: str
    identity_convention: str
    identity_hint: str
    accepted_constitutions: tuple[ConstitutionRef, ...] = ()
    declared_at: int = field(default_factory=lambda: int(time.time()))
    schema: str = HANDSHAKE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != HANDSHAKE_SCHEMA:
            raise HandshakeError(f"unsupported handshake schema: {self.schema}")
        if not isinstance(self.runtime, str) or not _RUNTIME.fullmatch(self.runtime):
            raise HandshakeError("runtime must be a lowercase safe identifier")
        if not isinstance(self.runtime_version, str) or not self.runtime_version.strip():
            raise HandshakeError("runtime_version is required")
        if len(self.runtime_version) > 128:
            raise HandshakeError("runtime_version cannot exceed 128 characters")
        if self.identity_convention not in _IDENTITY_CONVENTIONS:
            raise HandshakeError("identity_convention is not supported")
        if not isinstance(self.identity_hint, str) or len(self.identity_hint) > 500:
            raise HandshakeError("identity_hint must be a string of at most 500 characters")
        if not isinstance(self.declared_at, int) or isinstance(self.declared_at, bool):
            raise HandshakeError("declared_at must be an integer timestamp")
        if self.declared_at < 0:
            raise HandshakeError("declared_at cannot be negative")
        seen: set[tuple[str, str, str]] = set()
        for reference in self.accepted_constitutions:
            if not isinstance(reference, ConstitutionRef):
                raise HandshakeError("accepted constitutions must be ConstitutionRef instances")
            if reference.digest is None or not _DIGEST.fullmatch(reference.digest):
                raise HandshakeError("accepted constitutions must have exact sha256 digests")
            key = (reference.constitution_id, reference.version, reference.digest)
            if key in seen:
                raise HandshakeError("accepted constitutions must be unique")
            seen.add(key)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> RuntimeHandshake:
        data = dict(value)
        try:
            raw = data.get("accepted_constitutions", ())
            if not isinstance(raw, (list, tuple)):
                raise ValueError("accepted_constitutions must be an array")
            data["accepted_constitutions"] = tuple(ConstitutionRef(**item) for item in raw)
            return cls(**data)
        except (TypeError, ValueError) as error:
            if isinstance(error, HandshakeError):
                raise
            raise HandshakeError(f"invalid runtime handshake: {error}") from error

    @property
    def handshake_id(self) -> str:
        return digest(self.to_dict())


class FileHandshakeStore:
    """Immutable content-addressed storage for runtime handshakes."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def handshake_path(self, handshake_id: str) -> Path:
        if not _DIGEST.fullmatch(handshake_id):
            raise HandshakeError("handshake id must be a sha256 content address")
        return self.root / f"{handshake_id.removeprefix('sha256:')}.json"

    def record(self, handshake: RuntimeHandshake) -> str:
        path = self.handshake_path(handshake.handshake_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(handshake.to_dict(), sort_keys=True, indent=2) + "\n"
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(encoded)
        except FileExistsError:
            if self.get(handshake.handshake_id) != handshake:
                raise HandshakeIntegrityError(
                    "handshake content address already has different content"
                ) from None
        return handshake.handshake_id

    def get(self, handshake_id: str) -> RuntimeHandshake:
        path = self.handshake_path(handshake_id)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise HandshakeIntegrityError("runtime handshake must be a JSON object")
            handshake = RuntimeHandshake.from_dict(value)
        except (OSError, json.JSONDecodeError, HandshakeError) as error:
            if isinstance(error, HandshakeIntegrityError):
                raise
            raise HandshakeIntegrityError(f"invalid runtime handshake: {error}") from error
        if handshake.handshake_id != handshake_id:
            raise HandshakeIntegrityError(
                "runtime handshake filename does not match its content address"
            )
        return handshake

    def list(self) -> _HandshakeList:
        if not self.root.exists():
            return []
        return [
            self.get(f"sha256:{path.stem}")
            for path in sorted(self.root.glob("*.json"))
        ]

    def by_runtime(self, runtime: str) -> _HandshakeList:
        return [handshake for handshake in self.list() if handshake.runtime == runtime]
