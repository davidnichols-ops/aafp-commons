"""AAFP transport adapter for signed knowledge packets."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from aafp_commons.adoption import (
    ADOPTION_BOUNDARY,
    AdoptionRequestError,
    ConstitutionAdoptionRequest,
)
from aafp_commons.canonical import canonical_json
from aafp_commons.handshake import (
    HANDSHAKE_BOUNDARY,
    HandshakeError,
    RuntimeHandshake,
)
from aafp_commons.signing import SignedPacket

try:
    import aafp_py  # type: ignore[import-untyped]

    AAFP_AVAILABLE = True
except ImportError:
    aafp_py = None
    AAFP_AVAILABLE = False


class AafpTransportUnavailable(RuntimeError):
    pass


class AafpTransportProtocolError(ValueError):
    """Raised when an AAFP response is not a valid machine-readable object."""


def _decode_response(body: str) -> dict[str, Any]:
    try:
        result = json.loads(body)
    except json.JSONDecodeError as error:
        raise AafpTransportProtocolError("AAFP response is not valid JSON") from error
    if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
        raise AafpTransportProtocolError("AAFP response must be an object with boolean ok")
    return result


def _reject_unknown(value: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"{label} contains unknown fields: {', '.join(unknown)}")


ADOPTION_ENVELOPE_SCHEMA = "aafp.commons/constitution-adoption-envelope@1"
ADOPTION_CAPABILITY = "constitution-adoption"
HANDSHAKE_ENVELOPE_SCHEMA = "aafp.commons/runtime-handshake-envelope@1"
HANDSHAKE_CAPABILITY = "runtime-handshake"


def encode_adoption_request(request: ConstitutionAdoptionRequest) -> bytes:
    """Encode an unsigned adoption request for the AAFP capability."""
    return canonical_json({
        "schema": ADOPTION_ENVELOPE_SCHEMA,
        "request": request.to_dict(),
        "request_id": request.request_id,
        "boundary": ADOPTION_BOUNDARY,
    })


def decode_adoption_request(payload: bytes | str) -> ConstitutionAdoptionRequest:
    """Decode and content-address-check an adoption envelope."""
    try:
        value = json.loads(payload)
        if not isinstance(value, dict) or value.get("schema") != ADOPTION_ENVELOPE_SCHEMA:
            raise AdoptionRequestError("invalid constitution-adoption envelope schema")
        _reject_unknown(value, {"schema", "request", "request_id", "boundary"}, "adoption envelope")
        if value.get("boundary") != ADOPTION_BOUNDARY:
            raise AdoptionRequestError("constitution-adoption envelope boundary is invalid")
        raw_request = value.get("request")
        if not isinstance(raw_request, dict):
            raise AdoptionRequestError("constitution-adoption envelope lacks a request")
        request = ConstitutionAdoptionRequest.from_dict(raw_request)
        if value.get("request_id") != request.request_id:
            raise AdoptionRequestError("adoption envelope request id does not match its content")
        return request
    except (json.JSONDecodeError, TypeError, ValueError, AdoptionRequestError) as error:
        if isinstance(error, AdoptionRequestError):
            raise
        raise AdoptionRequestError(f"invalid constitution-adoption envelope: {error}") from error


def encode_runtime_handshake(handshake: RuntimeHandshake) -> bytes:
    """Encode an unsigned runtime handshake for the AAFP capability."""
    return canonical_json({
        "schema": HANDSHAKE_ENVELOPE_SCHEMA,
        "handshake": handshake.to_dict(),
        "handshake_id": handshake.handshake_id,
        "boundary": HANDSHAKE_BOUNDARY,
    })


def decode_runtime_handshake(payload: bytes | str) -> RuntimeHandshake:
    """Decode and content-address-check a runtime handshake envelope."""
    try:
        value = json.loads(payload)
        if not isinstance(value, dict) or value.get("schema") != HANDSHAKE_ENVELOPE_SCHEMA:
            raise HandshakeError("invalid runtime-handshake envelope schema")
        _reject_unknown(
            value, {"schema", "handshake", "handshake_id", "boundary"}, "handshake envelope"
        )
        if value.get("boundary") != HANDSHAKE_BOUNDARY:
            raise HandshakeError("runtime-handshake envelope boundary is invalid")
        raw_handshake = value.get("handshake")
        if not isinstance(raw_handshake, dict):
            raise HandshakeError("runtime-handshake envelope lacks a handshake")
        handshake = RuntimeHandshake.from_dict(raw_handshake)
        if value.get("handshake_id") != handshake.handshake_id:
            raise HandshakeError("runtime-handshake envelope id does not match its content")
        return handshake
    except (json.JSONDecodeError, TypeError, ValueError, HandshakeError) as error:
        if isinstance(error, HandshakeError):
            raise
        raise HandshakeError(f"invalid runtime-handshake envelope: {error}") from error


class AafpPacketTransport:
    """Send already-signed packets over AAFP's `knowledge-packet` capability."""

    def __init__(self) -> None:
        if not AAFP_AVAILABLE:
            raise AafpTransportUnavailable(
                "aafp-py is unavailable; build the local AAFP Python binding first"
            )
        self._server: Any | None = None

    async def send(self, address: str, packet: SignedPacket) -> dict[str, Any]:
        assert aafp_py is not None
        client = await aafp_py.SimpleAgent.connect()
        response = await client.call_at(
            address,
            aafp_py.Request.data(canonical_json(packet.to_dict())),
        )

        return _decode_response(response.body)

    async def serve(
        self,
        handler: Callable[[SignedPacket], Awaitable[dict[str, Any]]],
        bind: str = "127.0.0.1:0",
    ) -> Any:
        assert aafp_py is not None

        async def receive(request: Any) -> Any:
            payload = request.payload
            if payload is None:
                payload = request.body.encode("utf-8")
            signed = SignedPacket.from_dict(json.loads(payload))
            if not signed.verify():
                return aafp_py.Response.text(json.dumps({"ok": False, "error": "invalid packet"}))
            result = await handler(signed)
            return aafp_py.Response.text(json.dumps(result))

        builder = aafp_py.SimpleAgent.serve("knowledge-packet")
        builder.bind(bind)
        builder.handler(receive)
        self._server = await builder.start()
        return self._server

    async def close(self) -> None:
        if self._server is not None:
            self._server.stop()


class AafpConstitutionTransport:
    """Send unsigned agent adoption requests over a separate AAFP capability."""

    def __init__(self) -> None:
        if not AAFP_AVAILABLE:
            raise AafpTransportUnavailable(
                "aafp-py is unavailable; build the local AAFP Python binding first"
            )
        self._server: Any | None = None

    async def send_request(
        self, address: str, request: ConstitutionAdoptionRequest
    ) -> dict[str, Any]:
        assert aafp_py is not None
        client = await aafp_py.SimpleAgent.connect()
        response = await client.call_at(
            address,
            aafp_py.Request.data(encode_adoption_request(request)),
        )
        return _decode_response(response.body)

    async def serve(
        self,
        handler: Callable[[ConstitutionAdoptionRequest], Awaitable[dict[str, Any]]],
        bind: str = "127.0.0.1:0",
    ) -> Any:
        assert aafp_py is not None

        async def receive(request: Any) -> Any:
            payload = request.payload
            if payload is None:
                payload = request.body.encode("utf-8")
            try:
                adoption_request = decode_adoption_request(payload)
            except AdoptionRequestError as error:
                return aafp_py.Response.text(json.dumps({"ok": False, "error": str(error)}))
            result = await handler(adoption_request)
            return aafp_py.Response.text(json.dumps(result))

        builder = aafp_py.SimpleAgent.serve(ADOPTION_CAPABILITY)
        builder.bind(bind)
        builder.handler(receive)
        self._server = await builder.start()
        return self._server

    async def close(self) -> None:
        if self._server is not None:
            self._server.stop()


class AafpRuntimeHandshakeTransport:
    """Send unsigned runtime self-descriptions over a separate AAFP capability."""

    def __init__(self) -> None:
        if not AAFP_AVAILABLE:
            raise AafpTransportUnavailable(
                "aafp-py is unavailable; build the local AAFP Python binding first"
            )
        self._server: Any | None = None

    async def send_handshake(
        self, address: str, handshake: RuntimeHandshake
    ) -> dict[str, Any]:
        assert aafp_py is not None
        client = await aafp_py.SimpleAgent.connect()
        response = await client.call_at(
            address,
            aafp_py.Request.data(encode_runtime_handshake(handshake)),
        )
        return _decode_response(response.body)

    async def serve(
        self,
        handler: Callable[[RuntimeHandshake], Awaitable[dict[str, Any]]],
        bind: str = "127.0.0.1:0",
    ) -> Any:
        assert aafp_py is not None

        async def receive(request: Any) -> Any:
            payload = request.payload
            if payload is None:
                payload = request.body.encode("utf-8")
            try:
                handshake = decode_runtime_handshake(payload)
            except HandshakeError as error:
                return aafp_py.Response.text(json.dumps({"ok": False, "error": str(error)}))
            result = await handler(handshake)
            return aafp_py.Response.text(json.dumps(result))

        builder = aafp_py.SimpleAgent.serve(HANDSHAKE_CAPABILITY)
        builder.bind(bind)
        builder.handler(receive)
        self._server = await builder.start()
        return self._server

    async def close(self) -> None:
        if self._server is not None:
            self._server.stop()


class AafpJoinTransport:
    """Compose remote handshake and adoption-request transport calls."""

    def __init__(self) -> None:
        self.handshake = AafpRuntimeHandshakeTransport()
        self.adoption = AafpConstitutionTransport()

    async def send_join(
        self,
        address: str,
        handshake: RuntimeHandshake,
        request: ConstitutionAdoptionRequest,
    ) -> dict[str, Any]:
        """Send discovery first, then the exact adoption preference."""
        handshake_result = await self.handshake.send_handshake(address, handshake)
        if handshake_result.get("ok") is False:
            return {
                "handshake": handshake_result,
                "adoption": None,
                "handshake_id": handshake.handshake_id,
                "request_id": request.request_id,
                "joined": False,
            }
        if handshake_result.get("handshake_id") != handshake.handshake_id:
            return {
                "handshake": handshake_result,
                "adoption": None,
                "handshake_id": handshake.handshake_id,
                "request_id": request.request_id,
                "joined": False,
                "error": "remote handshake id does not match the sent handshake",
            }
        adoption_result = await self.adoption.send_request(address, request)
        if (
            adoption_result.get("ok") is True
            and adoption_result.get("request_id") != request.request_id
        ):
            return {
                "handshake": handshake_result,
                "adoption": adoption_result,
                "handshake_id": handshake.handshake_id,
                "request_id": request.request_id,
                "joined": False,
                "error": "remote adoption id does not match the sent request",
            }
        return {
            "handshake": handshake_result,
            "adoption": adoption_result,
            "handshake_id": handshake.handshake_id,
            "request_id": request.request_id,
            "joined": adoption_result.get("ok") is not False,
        }

    async def close(self) -> None:
        await self.handshake.close()
        await self.adoption.close()
