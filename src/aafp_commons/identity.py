"""AAFP identity references.

AAFP AgentId derivation is SHA-256(public_key), matching RFC-0003 and the
independent Go implementation. Identity validity and authority remain separate
from Ironclad signing-key validity.
"""

from __future__ import annotations

import hashlib
import re

AGENT_ID_PATTERN = re.compile(r"^aafp:[0-9a-f]{64}$")


def derive_agent_id(public_key: bytes) -> str:
    if not public_key:
        raise ValueError("public key cannot be empty")
    return f"aafp:{hashlib.sha256(public_key).hexdigest()}"


def validate_agent_id(agent_id: str) -> None:
    if not AGENT_ID_PATTERN.fullmatch(agent_id):
        raise ValueError("agent_id must be 'aafp:' followed by 64 lowercase hex characters")

