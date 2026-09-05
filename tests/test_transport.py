from __future__ import annotations

import asyncio

import pytest
from ironclad.trust import Identity

from aafp_commons.adoption import ConstitutionAdoptionRequest
from aafp_commons.handshake import RuntimeHandshake
from aafp_commons.identity import derive_agent_id
from aafp_commons.models import ConstitutionRef, KnowledgePacket
from aafp_commons.signing import sign_packet
from aafp_commons.transport import (
    AAFP_AVAILABLE,
    ADOPTION_ENVELOPE_SCHEMA,
    HANDSHAKE_ENVELOPE_SCHEMA,
    AafpConstitutionTransport,
    AafpPacketTransport,
    AafpRuntimeHandshakeTransport,
    decode_adoption_request,
    decode_runtime_handshake,
    encode_adoption_request,
    encode_runtime_handshake,
)


def test_join_transport_orders_handshake_before_adoption(monkeypatch: object) -> None:
    from aafp_commons.transport import AafpJoinTransport

    events: list[str] = []

    class FakeHandshake:
        async def send_handshake(self, address: str, handshake: object) -> dict[str, object]:
            events.append("handshake")
            return {"ok": True, "handshake_id": "h"}

        async def close(self) -> None:
            pass

    class FakeAdoption:
        async def send_request(self, address: str, request: object) -> dict[str, object]:
            events.append("adoption")
            return {"ok": True, "request_id": "r"}

        async def close(self) -> None:
            pass

    transport = AafpJoinTransport.__new__(AafpJoinTransport)
    transport.handshake = FakeHandshake()
    transport.adoption = FakeAdoption()
    import asyncio
    handshake = type("Handshake", (), {"handshake_id": "h"})()
    request = type("Request", (), {"request_id": "r"})()
    result = asyncio.run(transport.send_join("127.0.0.1:1", handshake, request))
    assert events == ["handshake", "adoption"]
    assert result["handshake"] == {"ok": True, "handshake_id": "h"}
    assert result["adoption"] == {"ok": True, "request_id": "r"}


def test_join_transport_fails_closed_on_handshake_rejection() -> None:
    from aafp_commons.transport import AafpJoinTransport
    events: list[str] = []

    class FakeHandshake:
        async def send_handshake(self, address: str, handshake: object) -> dict[str, object]:
            events.append("handshake")
            return {"ok": False, "error": "not supported"}

    class FakeAdoption:
        async def send_request(self, address: str, request: object) -> dict[str, object]:
            events.append("adoption")
            return {"ok": True}

    transport = AafpJoinTransport.__new__(AafpJoinTransport)
    transport.handshake = FakeHandshake()
    transport.adoption = FakeAdoption()
    import asyncio
    handshake = type("Handshake", (), {"handshake_id": "h"})()
    request = type("Request", (), {"request_id": "r"})()
    result = asyncio.run(transport.send_join("addr", handshake, request))
    assert events == ["handshake"]
    assert result["joined"] is False
    assert result["adoption"] is None


def test_transport_response_requires_boolean_ok() -> None:
    import pytest

    from aafp_commons.transport import AafpTransportProtocolError, _decode_response
    with pytest.raises(AafpTransportProtocolError):
        _decode_response("{}")
    with pytest.raises(AafpTransportProtocolError):
        _decode_response("[]")


def test_envelope_decoders_reject_unknown_fields() -> None:
    import json

    import pytest

    from aafp_commons.transport import decode_adoption_request, decode_runtime_handshake

    with pytest.raises(ValueError, match="unknown fields"):
        decode_adoption_request(json.dumps({"schema": ADOPTION_ENVELOPE_SCHEMA, "extra": 1}))
    with pytest.raises(ValueError, match="unknown fields"):
        decode_runtime_handshake(json.dumps({"schema": HANDSHAKE_ENVELOPE_SCHEMA, "extra": 1}))


def test_join_transport_rejects_mismatched_handshake_id() -> None:
    from aafp_commons.transport import AafpJoinTransport
    events: list[str] = []

    class FakeHandshake:
        async def send_handshake(self, address: str, handshake: object) -> dict[str, object]:
            return {"ok": True, "handshake_id": "wrong"}

    class FakeAdoption:
        async def send_request(self, address: str, request: object) -> dict[str, object]:
            events.append("adoption")
            return {"ok": True}

    transport = AafpJoinTransport.__new__(AafpJoinTransport)
    transport.handshake = FakeHandshake()
    transport.adoption = FakeAdoption()
    import asyncio
    handshake = type("Handshake", (), {"handshake_id": "expected"})()
    request = type("Request", (), {"request_id": "r"})()
    result = asyncio.run(transport.send_join("addr", handshake, request))
    assert result["joined"] is False
    assert events == []


def test_join_transport_rejects_mismatched_adoption_id() -> None:
    from aafp_commons.transport import AafpJoinTransport

    class FakeHandshake:
        async def send_handshake(self, address: str, handshake: object) -> dict[str, object]:
            return {"ok": True, "handshake_id": "expected"}

    class FakeAdoption:
        async def send_request(self, address: str, request: object) -> dict[str, object]:
            return {"ok": True, "request_id": "wrong"}

    transport = AafpJoinTransport.__new__(AafpJoinTransport)
    transport.handshake = FakeHandshake()
    transport.adoption = FakeAdoption()
    import asyncio
    handshake = type("Handshake", (), {"handshake_id": "expected"})()
    request = type("Request", (), {"request_id": "expected-request"})()
    result = asyncio.run(transport.send_join("addr", handshake, request))
    assert result["joined"] is False
    assert "adoption id" in result["error"]


def test_adoption_envelope_round_trip_and_tamper_detection() -> None:
    request = ConstitutionAdoptionRequest(
        requester_agent_id=derive_agent_id(b"transport-agent"),
        runtime="grok",
        namespace="commons/frontend/react",
        packet_kind="finding",
        constitution=ConstitutionRef(
            "grok-truth-seeking", "1.0.0", "sha256:" + "a" * 64
        ),
        created_at=10,
    )
    encoded = encode_adoption_request(request)
    assert decode_adoption_request(encoded) == request
    assert request.request_id.encode() in encoded
    assert ADOPTION_ENVELOPE_SCHEMA.encode() in encoded
    tampered = encoded.replace(
        request.request_id.encode(), ("sha256:" + "b" * 64).encode(), 1
    )
    with pytest.raises(ValueError, match="request id"):
        decode_adoption_request(tampered)
    boundary_tampered = encoded.replace(b"does not prove AAFP identity", b"may prove AAFP identity")
    with pytest.raises(ValueError, match="boundary"):
        decode_adoption_request(boundary_tampered)


def test_runtime_handshake_envelope_round_trip_and_tamper_detection() -> None:
    handshake = RuntimeHandshake(
        runtime="grok",
        runtime_version="3",
        identity_convention="runtime-native",
        identity_hint="session key",
        declared_at=10,
    )
    encoded = encode_runtime_handshake(handshake)
    assert decode_runtime_handshake(encoded) == handshake
    assert HANDSHAKE_ENVELOPE_SCHEMA.encode() in encoded
    tampered = encoded.replace(
        handshake.handshake_id.encode(), ("sha256:" + "b" * 64).encode(), 1
    )
    with pytest.raises(ValueError, match="id"):
        decode_runtime_handshake(tampered)


@pytest.mark.skipif(not AAFP_AVAILABLE, reason="local aafp-py binding is not installed")
def test_signed_packet_round_trip_over_aafp(
    packet: KnowledgePacket, identity: Identity
) -> None:
    async def exercise() -> None:
        server = AafpPacketTransport()

        async def accept(received):  # type: ignore[no-untyped-def]
            return {"ok": True, "packet_id": received.packet_id}

        serving = await server.serve(accept)
        client = AafpPacketTransport()
        try:
            signed = sign_packet(packet, identity)
            response = await client.send(serving.addr, signed)
            assert response == {"ok": True, "packet_id": packet.packet_id}
        finally:
            await client.close()
            await server.close()

    asyncio.run(exercise())


@pytest.mark.skipif(not AAFP_AVAILABLE, reason="local aafp-py binding is not installed")
def test_adoption_request_round_trip_over_aafp() -> None:
    async def exercise() -> None:
        server = AafpConstitutionTransport()
        request = ConstitutionAdoptionRequest(
            requester_agent_id=derive_agent_id(b"transport-agent"),
            runtime="grok",
            namespace="commons/frontend/react",
            packet_kind="finding",
            constitution=ConstitutionRef(
                "grok-truth-seeking", "1.0.0", "sha256:" + "a" * 64
            ),
            created_at=10,
        )

        async def accept(received):  # type: ignore[no-untyped-def]
            return {"ok": True, "request_id": received.request_id}

        serving = await server.serve(accept)
        client = AafpConstitutionTransport()
        try:
            assert await client.send_request(serving.addr, request) == {
                "ok": True,
                "request_id": request.request_id,
            }
        finally:
            await client.close()
            await server.close()

    asyncio.run(exercise())


@pytest.mark.skipif(not AAFP_AVAILABLE, reason="local aafp-py binding is not installed")
def test_runtime_handshake_round_trip_over_aafp() -> None:
    async def exercise() -> None:
        server = AafpRuntimeHandshakeTransport()
        handshake = RuntimeHandshake(
            runtime="grok",
            runtime_version="3",
            identity_convention="runtime-native",
            identity_hint="session key",
            declared_at=10,
        )

        async def accept(received):  # type: ignore[no-untyped-def]
            return {"ok": True, "handshake_id": received.handshake_id}

        serving = await server.serve(accept)
        client = AafpRuntimeHandshakeTransport()
        try:
            assert await client.send_handshake(serving.addr, handshake) == {
                "ok": True,
                "handshake_id": handshake.handshake_id,
            }
        finally:
            await client.close()
            await server.close()

    asyncio.run(exercise())
