from __future__ import annotations

import io
import json
import time
from pathlib import Path

import pytest
from ironclad.trust import Identity

from aafp_commons.identity import derive_agent_id
from aafp_commons.mcp_stdio import serve_stdio
from aafp_commons.models import KnowledgePacket
from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import sign_packet
from aafp_commons.ucan import (
    UCAN_COMMAND,
    UCAN_GLOBAL_RESOURCE,
    UcanError,
    did_key_from_public_key,
    encode_ucan,
    verify_ucan,
)
from aafp_commons.w1 import _load_identity, main


def _token(packet: KnowledgePacket, *, capability: str = UCAN_GLOBAL_RESOURCE) -> str:
    issuer = Identity.generate()
    audience = Identity.generate()
    return encode_ucan(
        issuer,
        {
            "aud": did_key_from_public_key(audience.public_bytes()),
            "sub": packet.author_agent_id,
            "cmd": UCAN_COMMAND,
            "args": {"namespace": packet.namespace},
            "nonce": "test-nonce",
            "exp": int(time.time()) + 300,
            "att": [{"with": capability, "can": UCAN_COMMAND}],
        },
    )


def _repository(tmp_path: Path, constitution, packet: KnowledgePacket, identity: Identity):
    repository = CommonsRepository(tmp_path)
    repository.install_constitution(constitution)
    return repository, sign_packet(packet, identity)


def test_submit_without_ucan_remains_compatible(
    tmp_path, packet, identity, constitution, monkeypatch
):
    monkeypatch.delenv("COMMONS_REQUIRE_UCAN", raising=False)
    repository, signed = _repository(tmp_path, constitution, packet, identity)
    assert repository.submit(signed, identity).accepted


def test_required_mode_denies_missing_ucan(tmp_path, packet, identity, constitution, monkeypatch):
    monkeypatch.setenv("COMMONS_REQUIRE_UCAN", "1")
    repository, signed = _repository(tmp_path, constitution, packet, identity)
    decision = repository.submit(signed, identity)
    assert not decision.accepted
    assert "UCAN_REQUIRED" in decision.reasons


def test_valid_global_ucan_admits_packet(tmp_path, packet, identity, constitution, monkeypatch):
    monkeypatch.setenv("COMMONS_REQUIRE_UCAN", "1")
    repository, signed = _repository(tmp_path, constitution, packet, identity)
    decision = repository.submit(signed, identity, ucan=_token(packet))
    assert decision.accepted


def test_valid_namespace_ucan_admits_packet(tmp_path, packet, identity, constitution, monkeypatch):
    monkeypatch.setenv("COMMONS_REQUIRE_UCAN", "1")
    repository, signed = _repository(tmp_path, constitution, packet, identity)
    capability = f"commons://namespace/{packet.namespace}"
    decision = repository.submit(signed, identity, ucan=_token(packet, capability=capability))
    assert decision.accepted


def test_configured_audience_is_enforced(packet, monkeypatch):
    monkeypatch.setenv(
        "COMMONS_UCAN_AUDIENCE",
        did_key_from_public_key(Identity.generate().public_bytes()),
    )
    with pytest.raises(UcanError, match="audience"):
        verify_ucan(_token(packet), packet)


@pytest.mark.parametrize(
    "mutate,expected",
    [
            (lambda token, packet: "not.a.ucan", "UCAN_INVALID"),
            (
                lambda token, packet: token.rsplit(".", 1)[0]
                + ".A"
                + token.rsplit(".", 1)[1][1:],
                "UCAN_INVALID",
            ),
        (
            lambda token, packet: encode_ucan(
                Identity.generate(),
                {
                    "aud": did_key_from_public_key(Identity.generate().public_bytes()),
                    "sub": packet.author_agent_id,
                    "cmd": UCAN_COMMAND,
                    "args": {"namespace": packet.namespace},
                    "nonce": "expired",
                    "exp": int(time.time()) - 1,
                    "att": [{"with": UCAN_GLOBAL_RESOURCE, "can": UCAN_COMMAND}],
                },
            ),
            "expired",
        ),
        (
            lambda token, packet: encode_ucan(
                Identity.generate(),
                {
                    "aud": did_key_from_public_key(Identity.generate().public_bytes()),
                    "sub": "aafp:" + "0" * 64,
                    "cmd": UCAN_COMMAND,
                    "args": {"namespace": packet.namespace},
                    "nonce": "wrong-subject",
                    "exp": int(time.time()) + 300,
                    "att": [{"with": UCAN_GLOBAL_RESOURCE, "can": UCAN_COMMAND}],
                },
            ),
            "subject",
        ),
        (
            lambda token, packet: encode_ucan(
                Identity.generate(),
                {
                    "aud": did_key_from_public_key(Identity.generate().public_bytes()),
                    "sub": packet.author_agent_id,
                    "cmd": UCAN_COMMAND,
                    "args": {"namespace": packet.namespace},
                    "nonce": "wrong-capability",
                    "exp": int(time.time()) + 300,
                    "att": [{"with": "commons://other", "can": UCAN_COMMAND}],
                },
            ),
            "capability",
        ),
    ],
)
def test_invalid_ucan_is_denied(packet, mutate, expected):
    token = _token(packet)
    with pytest.raises(UcanError, match=expected):
        verify_ucan(mutate(token, packet), packet)


def test_proof_chain_is_denied(packet):
    issuer = Identity.generate()
    token = encode_ucan(
        issuer,
        {
            "aud": did_key_from_public_key(Identity.generate().public_bytes()),
            "sub": packet.author_agent_id,
            "cmd": UCAN_COMMAND,
            "args": {"namespace": packet.namespace},
            "nonce": "proof-chain",
            "exp": int(time.time()) + 300,
            "att": [{"with": UCAN_GLOBAL_RESOURCE, "can": UCAN_COMMAND}],
            "prf": ["parent-ucan"],
        },
    )
    with pytest.raises(UcanError, match="proof chains"):
        verify_ucan(token, packet)


def test_mcp_propose_forwards_ucan(tmp_path: Path, monkeypatch, capsys) -> None:
    home = tmp_path / "subject"
    monkeypatch.setenv("COMMONS_HOME", str(home))
    monkeypatch.setenv("COMMONS_REQUIRE_UCAN", "1")
    assert main(["init"]) == 0
    capsys.readouterr()
    identity = _load_identity(home)
    assert identity is not None
    issuer = Identity.generate()
    audience = Identity.generate()
    namespace = "commons/mcp-ucan"
    token = encode_ucan(
        issuer,
        {
            "aud": did_key_from_public_key(audience.public_bytes()),
            "sub": derive_agent_id(identity.public_bytes()),
            "cmd": UCAN_COMMAND,
            "args": {"namespace": namespace},
            "nonce": "mcp-propose",
            "exp": int(time.time()) + 300,
            "att": [{"with": UCAN_GLOBAL_RESOURCE, "can": UCAN_COMMAND}],
        },
    )
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "commons_propose",
            "arguments": {
                "namespace": namespace,
                "claim": "An MCP UCAN admission is evidence-backed.",
                "evidence": [{"kind": "test", "uri": "artifact://ucan"}],
                "ucan": token,
            },
        },
    }
    incoming = io.BytesIO((json.dumps(request) + "\n").encode())
    outgoing = io.BytesIO()
    assert serve_stdio(incoming, outgoing, home) == 0
    response = json.loads(outgoing.getvalue().splitlines()[0])
    assert response["result"]["isError"] is False
