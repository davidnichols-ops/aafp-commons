"""Canonical content addressing (CBOR + SHA-256).

Reimplementation of the ``ironclad.canon`` surface consumed by
``aafp_commons``. The wire format is:

- ``content_digest(obj)`` → ``sha256:<base64url-no-pad(sha256(canonical_cbor(obj)))>``
- ``canonical_cbor(obj)`` → ``cbor2.dumps(_sort_keys(obj), canonical=True)``

``_sort_keys`` recursively sorts dict keys, maps lists element-wise, and
normalizes floats (``-0.0`` → ``0.0``, strips trailing zeros via ``.17g``
formatting) so that semantically-equal values produce identical bytes.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

import cbor2


def _sort_keys(value: Any) -> Any:
    """Recursively sort dict keys and normalize floats for deterministic encoding."""
    if isinstance(value, dict):
        return {k: _sort_keys(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_sort_keys(v) for v in value]
    if isinstance(value, float):
        if value == 0.0:
            return 0.0
        s = format(value, ".17g").rstrip("0").rstrip(".")
        if s in ("", "-"):
            return 0.0
        return float(s)
    return value


def canonical_cbor(value: Any) -> bytes:
    """Encode *value* as canonical CBOR with sorted keys and normalized floats."""
    return cbor2.dumps(_sort_keys(value), canonical=True)


def canonical_json(value: Any) -> bytes:
    """Encode *value* as canonical JSON with sorted keys and normalized floats."""
    return json.dumps(
        _sort_keys(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=False,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256b64(data: bytes) -> str:
    """Return the base64url (no padding) encoding of ``sha256(data)``."""
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")


def sha256hex(data: bytes) -> str:
    """Return the hex encoding of ``sha256(data)``."""
    return hashlib.sha256(data).hexdigest()


def content_digest(obj: Any, *, use_cbor: bool = True) -> str:
    """Content-address *obj* as ``sha256:<base64url>`` of its canonical encoding.

    By default the canonical encoding is CBOR (matching the
    ``ironclad-ed25519-v1`` wire format). Pass ``use_cbor=False`` for the
    JSON encoding path.
    """
    payload = canonical_cbor(obj) if use_cbor else canonical_json(obj)
    return f"sha256:{sha256b64(payload)}"
