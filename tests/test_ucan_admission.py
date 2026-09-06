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


@pytest.fixture
def grant(packet, identity, monkeypatch):
    issuer = Identity.generate()
    audience = did_key_from_public_key(Identity.generate().public_bytes())
    monkeypatch.setenv("COMMONS_UCAN_AUDIENCE", audience)
    monkeypatch.setenv(
        "COMMONS_UCAN_TRUSTED_ISSUERS",
        json.dumps({did_key_from_public_key(issuer.public_bytes()): [UCAN_GLOBAL_RESOURCE]}),
    )
    return issuer, {
        "aud": audience,
        "sub": packet.author_agent_id,
        "cmd": UCAN_COMMAND,
        "args": {"namespace": packet.namespace, "signer_key_id": identity.key_id},
        "nonce": "test-nonce",
        "exp": int(time.time()) + 300,
        "att": [{"with": UCAN_GLOBAL_RESOURCE, "can": UCAN_COMMAND}],
    }


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


def test_valid_global_ucan_admits_packet(
    tmp_path, packet, identity, constitution, monkeypatch, grant
):
    monkeypatch.setenv("COMMONS_REQUIRE_UCAN", "1")
    repository, signed = _repository(tmp_path, constitution, packet, identity)
    decision = repository.submit(signed, identity, ucan=encode_ucan(*grant))
    assert decision.accepted


def test_valid_namespace_ucan_admits_packet(
    tmp_path, packet, identity, constitution, monkeypatch, grant
):
    monkeypatch.setenv("COMMONS_REQUIRE_UCAN", "1")
    repository, signed = _repository(tmp_path, constitution, packet, identity)
    capability = f"commons://namespace/{packet.namespace}"
    issuer, payload = grant
    payload["att"] = [{"with": capability, "can": UCAN_COMMAND}]
    decision = repository.submit(signed, identity, ucan=encode_ucan(issuer, payload))
    assert decision.accepted


def test_configured_audience_is_enforced(packet, identity, monkeypatch, grant):
    monkeypatch.setenv(
        "COMMONS_UCAN_AUDIENCE",
        did_key_from_public_key(Identity.generate().public_bytes()),
    )
    with pytest.raises(UcanError, match="audience"):
        verify_ucan(encode_ucan(*grant), packet, signer_key_id=identity.key_id)


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"exp": 0}, "expired"),
        ({"exp": True}, "integer"),
        ({"nbf": 2**53}, "not yet valid"),
        ({"nbf": True}, "integer"),
        ({"sub": "aafp:" + "0" * 64}, "subject"),
        ({"cmd": "commons/read"}, "command"),
        ({"nonce": ""}, "nonce"),
        ({"att": []}, "capability"),
        ({"att": [{"with": "commons://other", "can": UCAN_COMMAND}]}, "capability"),
        ({"prf": ["parent-ucan"]}, "proof chains"),
        ({"unknown_caveat": "deny"}, "unsupported token"),
    ],
)
def test_invalid_ucan_is_denied(packet, identity, grant, changes, expected):
    issuer, payload = grant
    payload.update(changes)
    with pytest.raises(UcanError, match=expected):
        verify_ucan(encode_ucan(issuer, payload), packet, signer_key_id=identity.key_id)


def test_bad_signature_is_denied(packet, identity, grant):
    token = encode_ucan(*grant)
    header_payload, signature = token.rsplit(".", 1)
    changed = ("B" if signature[0] == "A" else "A") + signature[1:]
    with pytest.raises(UcanError, match="UCAN_INVALID"):
        verify_ucan(f"{header_payload}.{changed}", packet, signer_key_id=identity.key_id)


@pytest.mark.parametrize("case", ["valid", "untrusted", "missing", "wrong-signer"])
def test_mcp_propose_forwards_ucan(tmp_path: Path, monkeypatch, capsys, case) -> None:
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
    monkeypatch.setenv("COMMONS_UCAN_AUDIENCE", did_key_from_public_key(audience.public_bytes()))
    monkeypatch.setenv(
        "COMMONS_UCAN_TRUSTED_ISSUERS",
        json.dumps(
            {did_key_from_public_key(issuer.public_bytes()): [f"commons://namespace/{namespace}"]}
        ),
    )
    token = encode_ucan(
        Identity.generate() if case == "untrusted" else issuer,
        {
            "aud": did_key_from_public_key(audience.public_bytes()),
            "sub": derive_agent_id(identity.public_bytes()),
            "cmd": UCAN_COMMAND,
            "args": {
                "namespace": namespace,
                "signer_key_id": "different-key" if case == "wrong-signer" else identity.key_id,
            },
            "nonce": "mcp-propose",
            "exp": int(time.time()) + 300,
            "att": [{"with": f"commons://namespace/{namespace}", "can": UCAN_COMMAND}],
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
    if case == "missing":
        del request["params"]["arguments"]["ucan"]
    incoming = io.BytesIO((json.dumps(request) + "\n").encode())
    outgoing = io.BytesIO()
    assert serve_stdio(incoming, outgoing, home) == 0
    response = json.loads(outgoing.getvalue().splitlines()[0])
    result = response["result"]
    assert result["isError"] is (case != "valid")
    if case != "valid":
        expected = "UCAN_REQUIRED" if case == "missing" else "UCAN_INVALID"
        assert result["structuredContent"]["error"]["code"] == expected
        assert not CommonsRepository(home).query()
