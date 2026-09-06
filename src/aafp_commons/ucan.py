"""Minimal JWT-like UCAN verification for optional packet admission.

This module intentionally implements the bounded subset documented in
``docs/VENDOR.md``. It is an admission capability, not a replacement for
Ironclad packet signatures or a full UCAN delegation/invocation stack.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from ironclad.trust import Identity

from aafp_commons.canonical import b64decode, b64encode, canonical_json
from aafp_commons.models import KnowledgePacket

UCAN_ALGORITHM = "EdDSA"
UCAN_TYPE = "JWT"
UCAN_COMMAND = "commons/submit"
UCAN_GLOBAL_RESOURCE = "commons://aafp-commons"
UCAN_NAMESPACE_PREFIX = "commons://namespace/"

_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_ED25519_MULTICODEC = b"\xed\x01"
_MAX_TOKEN_LENGTH = 16_384


class UcanError(ValueError):
    """Raised when a bounded UCAN admission token is invalid."""


@dataclass(frozen=True)
class UcanClaims:
    issuer: str
    audience: str
    subject: str
    payload: dict[str, Any]


def did_key_from_public_key(public_key: bytes) -> str:
    """Return the UCAN ``did:key`` representation for an Ed25519 key."""
    if len(public_key) != 32:
        raise ValueError("Ed25519 public key must be 32 bytes")
    return "did:key:z" + _base58_encode(_ED25519_MULTICODEC + public_key)


def encode_ucan(identity: Identity, payload: dict[str, Any]) -> str:
    """Create the documented JWT-like UCAN subset for tests and local clients."""
    body = dict(payload)
    issuer = did_key_from_public_key(identity.public_bytes())
    existing_issuer = body.setdefault("iss", issuer)
    if existing_issuer != issuer:
        raise ValueError("UCAN issuer does not match the signing identity")
    header = {"alg": UCAN_ALGORITHM, "typ": UCAN_TYPE}
    encoded_header = b64encode(canonical_json(header))
    encoded_payload = b64encode(canonical_json(body))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    return f"{encoded_header}.{encoded_payload}.{b64encode(identity.sign(signing_input))}"


def verify_ucan(
    token: str,
    packet: KnowledgePacket,
    *,
    now: int | None = None,
    expected_audience: str | None = None,
    trusted_issuers: dict[str, list[str]] | None = None,
    signer_key_id: str | None = None,
) -> UcanClaims:
    """Verify a grant against operator trust and the verified packet signer.

    Callers must verify the packet signature before trusting ``signer_key_id``.
    Explicit trust/audience arguments override environment configuration;
    missing or empty configuration never authorizes a supplied token.
    """
    try:
        header, payload, signature, signing_input = _decode(token)
        if header != {"alg": UCAN_ALGORITHM, "typ": UCAN_TYPE}:
            raise UcanError("UCAN_INVALID: unsupported header")
        if payload.keys() - {
            "iss",
            "aud",
            "sub",
            "cmd",
            "args",
            "nonce",
            "exp",
            "nbf",
            "att",
            "prf",
        }:
            raise UcanError("UCAN_INVALID: unsupported token fields")
        issuer = payload.get("iss")
        audience = payload.get("aud")
        subject = payload.get("sub")
        if not all(isinstance(value, str) and value for value in (issuer, audience, subject)):
            raise UcanError("UCAN_INVALID: iss, aud, and sub are required")
        public_key = _public_key_from_did(issuer)
        public_key.verify(signature, signing_input)
        _public_key_from_did(audience)
        if subject != packet.author_agent_id:
            raise UcanError("UCAN_INVALID: subject does not match packet author")
        configured_audience = (
            os.environ.get("COMMONS_UCAN_AUDIENCE")
            if expected_audience is None
            else expected_audience
        )
        if not configured_audience:
            raise UcanError("UCAN_INVALID: operator audience is not configured")
        _public_key_from_did(configured_audience)
        if audience != configured_audience:
            raise UcanError("UCAN_INVALID: audience does not match this Commons node")
        grants = _issuer_grants(trusted_issuers)
        if issuer not in grants:
            raise UcanError("UCAN_INVALID: issuer is not trusted by this Commons node")
        if payload.get("cmd") != UCAN_COMMAND:
            raise UcanError("UCAN_INVALID: command is not commons/submit")
        args = payload.get("args")
        if not isinstance(args, dict):
            raise UcanError("UCAN_INVALID: args must be an object")
        if args.keys() - {"namespace", "packet_id", "signer_key_id"}:
            raise UcanError("UCAN_INVALID: unsupported argument constraints")
        if (
            not isinstance(signer_key_id, str)
            or not signer_key_id
            or args.get("signer_key_id") != signer_key_id
        ):
            raise UcanError("UCAN_INVALID: signer_key_id does not match packet signer")
        if "namespace" in args and args["namespace"] != packet.namespace:
            raise UcanError("UCAN_INVALID: namespace does not match packet")
        if "packet_id" in args and args["packet_id"] != packet.packet_id:
            raise UcanError("UCAN_INVALID: packet_id does not match packet")
        _verify_time_bounds(payload, int(time.time()) if now is None else now)
        nonce = payload.get("nonce")
        if not isinstance(nonce, str) or not nonce.strip():
            raise UcanError("UCAN_INVALID: nonce is required")
        proofs = payload.get("prf", [])
        if not isinstance(proofs, list) or proofs:
            raise UcanError("UCAN_INVALID: proof chains are not supported")
        _verify_capabilities(payload.get("att"), packet.namespace, grants[issuer])
        return UcanClaims(issuer=issuer, audience=audience, subject=subject, payload=payload)
    except UcanError:
        raise
    except (InvalidSignature, KeyError, TypeError, ValueError, RecursionError) as error:
        raise UcanError(f"UCAN_INVALID: {error}") from error


def _decode(token: str) -> tuple[dict[str, Any], dict[str, Any], bytes, bytes]:
    if not isinstance(token, str) or len(token) > _MAX_TOKEN_LENGTH:
        raise UcanError("UCAN_INVALID: token must be a string of at most 16384 characters")
    parts = token.split(".")
    if len(parts) != 3 or any(not part for part in parts):
        raise UcanError("UCAN_INVALID: token must have three segments")
    decoded = []
    for part in parts:
        if re.fullmatch(r"[A-Za-z0-9_-]+", part) is None:
            raise UcanError("UCAN_INVALID: malformed base64url segment")
        value = b64decode(part)
        if b64encode(value) != part:
            raise UcanError("UCAN_INVALID: noncanonical base64url segment")
        decoded.append(value)
    header_bytes, payload_bytes, signature = decoded
    header = _load_json(header_bytes.decode("utf-8"))
    payload = _load_json(payload_bytes.decode("utf-8"))
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise UcanError("UCAN_INVALID: header and payload must be objects")
    return header, payload, signature, f"{parts[0]}.{parts[1]}".encode("ascii")


def _verify_time_bounds(payload: dict[str, Any], now: int) -> None:
    exp = payload.get("exp")
    if isinstance(exp, bool) or not isinstance(exp, int):
        raise UcanError("UCAN_INVALID: exp must be an integer")
    if exp <= now:
        raise UcanError("UCAN_INVALID: UCAN is expired")
    nbf = payload.get("nbf")
    if nbf is not None and (isinstance(nbf, bool) or not isinstance(nbf, int)):
        raise UcanError("UCAN_INVALID: nbf must be an integer")
    if nbf is not None and nbf > now:
        raise UcanError("UCAN_INVALID: UCAN is not yet valid")


def _load_json(value: str) -> Any:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise UcanError("UCAN_INVALID: duplicate JSON field")
            result[key] = item
        return result

    def reject_constant(value: str) -> None:
        raise UcanError("UCAN_INVALID: non-finite JSON value")

    return json.loads(value, object_pairs_hook=unique_object, parse_constant=reject_constant)


def _valid_resource(value: Any) -> bool:
    return isinstance(value, str) and (
        value == UCAN_GLOBAL_RESOURCE
        or (value.startswith(UCAN_NAMESPACE_PREFIX) and len(value) > len(UCAN_NAMESPACE_PREFIX))
    )


def _issuer_grants(configured: dict[str, list[str]] | None) -> dict[str, list[str]]:
    if configured is None:
        raw = os.environ.get("COMMONS_UCAN_TRUSTED_ISSUERS")
        configured = _load_json(raw) if raw else None
    if not isinstance(configured, dict) or not configured:
        raise UcanError("UCAN_INVALID: operator trusted issuers are not configured")
    for issuer, resources in configured.items():
        _public_key_from_did(issuer)
        if (
            not isinstance(resources, list)
            or not resources
            or not all(_valid_resource(resource) for resource in resources)
        ):
            raise UcanError("UCAN_INVALID: malformed operator issuer grants")
    return configured


def _verify_capabilities(value: Any, namespace: str, grants: list[str]) -> None:
    if not isinstance(value, list) or not value:
        raise UcanError("UCAN_INVALID: submit capability is missing")
    allowed_resources = {
        UCAN_GLOBAL_RESOURCE,
        f"{UCAN_NAMESPACE_PREFIX}{namespace}",
    }
    covers_packet = False
    for capability in value:
        if (
            not isinstance(capability, dict)
            or capability.keys() != {"with", "can"}
            or capability["can"] != UCAN_COMMAND
            or not _valid_resource(capability["with"])
        ):
            raise UcanError("UCAN_INVALID: unsupported submit capability or constraints")
        resource = capability["with"]
        if UCAN_GLOBAL_RESOURCE not in grants and resource not in grants:
            raise UcanError("UCAN_INVALID: capability exceeds issuer authority")
        covers_packet |= resource in allowed_resources
    if not covers_packet:
        raise UcanError("UCAN_INVALID: submit capability does not cover packet namespace")


def _public_key_from_did(value: str) -> Ed25519PublicKey:
    if not isinstance(value, str) or not value.startswith("did:key:z") or len(value) > 64:
        raise UcanError("UCAN_INVALID: issuer must be an Ed25519 did:key")
    decoded = _base58_decode(value.removeprefix("did:key:z"))
    if not decoded.startswith(_ED25519_MULTICODEC) or len(decoded) != 34:
        raise UcanError("UCAN_INVALID: issuer did:key is not Ed25519")
    return Ed25519PublicKey.from_public_bytes(decoded[2:])


def _base58_encode(value: bytes) -> str:
    number = int.from_bytes(value, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = _BASE58_ALPHABET[remainder] + encoded
    return _BASE58_ALPHABET[0] * (len(value) - len(value.lstrip(b"\0"))) + (encoded or "1")


def _base58_decode(value: str) -> bytes:
    if not value:
        raise UcanError("UCAN_INVALID: empty issuer key")
    number = 0
    for character in value:
        try:
            number = number * 58 + _BASE58_ALPHABET.index(character)
        except ValueError as error:
            raise UcanError("UCAN_INVALID: malformed issuer key") from error
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    return b"\0" * (len(value) - len(value.lstrip("1"))) + raw
