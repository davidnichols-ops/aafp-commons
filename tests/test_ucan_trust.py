"""Regressions for the self-issued permission bypass at the submit boundary."""

from __future__ import annotations

import json
import os
import time
from dataclasses import replace

import pytest
from ironclad.trust import Identity

from aafp_commons.canonical import b64encode, canonical_json
from aafp_commons.mcp_stdio import _handle
from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import sign_packet
from aafp_commons.ucan import (
    UCAN_COMMAND,
    UCAN_GLOBAL_RESOURCE,
    UCAN_NAMESPACE_PREFIX,
    UcanError,
    did_key_from_public_key,
    encode_ucan,
    verify_ucan,
)
from aafp_commons.w1 import main


@pytest.fixture
def admission(tmp_path, packet, identity, constitution, monkeypatch):
    issuer = Identity.generate()
    audience = did_key_from_public_key(Identity.generate().public_bytes())
    resource = UCAN_NAMESPACE_PREFIX + packet.namespace
    monkeypatch.setenv("COMMONS_REQUIRE_UCAN", "1")
    monkeypatch.setenv("COMMONS_UCAN_AUDIENCE", audience)
    monkeypatch.setenv(
        "COMMONS_UCAN_TRUSTED_ISSUERS",
        json.dumps(
            {
                did_key_from_public_key(issuer.public_bytes()): [resource],
            }
        ),
    )
    repository = CommonsRepository(tmp_path)
    repository.install_constitution(constitution)
    signed = sign_packet(packet, identity)
    payload = {
        "aud": audience,
        "sub": packet.author_agent_id,
        "cmd": UCAN_COMMAND,
        "args": {"namespace": packet.namespace, "signer_key_id": identity.key_id},
        "nonce": "trust-regression",
        "exp": int(time.time()) + 300,
        "att": [{"with": resource, "can": UCAN_COMMAND}],
    }
    return repository, signed, issuer, payload


def _assert_denied_without_writes(repository, signed, identity, token):
    decision = repository.submit(signed, identity, ucan=token)
    assert not decision.accepted, "unauthorized token must not admit a packet"
    assert any(reason.startswith("UCAN_INVALID") for reason in decision.reasons)
    assert not repository.objects_dir.exists()
    assert not (repository.root / "ledger.jsonl").exists()


def test_arbitrary_issuer_cannot_self_grant(admission, identity):
    repository, signed, _, payload = admission
    attacker = Identity.generate()
    token = encode_ucan(attacker, payload)
    _assert_denied_without_writes(repository, signed, identity, token)


@pytest.mark.parametrize("variable", ["COMMONS_UCAN_TRUSTED_ISSUERS", "COMMONS_UCAN_AUDIENCE"])
def test_missing_trust_configuration_denies(admission, identity, monkeypatch, variable):
    repository, signed, issuer, payload = admission
    monkeypatch.delenv(variable)
    _assert_denied_without_writes(repository, signed, identity, encode_ucan(issuer, payload))


def test_namespace_issuer_cannot_grant_global_authority(admission, identity):
    repository, signed, issuer, payload = admission
    payload["att"] = [{"with": UCAN_GLOBAL_RESOURCE, "can": UCAN_COMMAND}]
    _assert_denied_without_writes(repository, signed, identity, encode_ucan(issuer, payload))


def test_stolen_grant_cannot_be_used_by_another_packet_signer(admission, identity):
    repository, signed, issuer, payload = admission
    substituted = sign_packet(signed.packet, Identity.generate())
    _assert_denied_without_writes(repository, substituted, identity, encode_ucan(issuer, payload))


def test_valid_ucan_cannot_bypass_packet_signature(admission, identity):
    repository, signed, issuer, payload = admission
    forged = replace(sign_packet(signed.packet, Identity.generate()), signer_key_id=identity.key_id)
    decision = repository.submit(forged, identity, ucan=encode_ucan(issuer, payload))
    assert not decision.accepted
    assert "invalid Ironclad signature or receipt" in decision.reasons
    assert not repository.objects_dir.exists()
    assert not (repository.root / "ledger.jsonl").exists()


def test_valid_ucan_cannot_bypass_constitution_policy(admission, identity, monkeypatch):
    repository, signed, issuer, payload = admission
    denied_namespace = "commons/outside-constitution"
    changed = sign_packet(replace(signed.packet, namespace=denied_namespace), identity)
    resource = UCAN_NAMESPACE_PREFIX + denied_namespace
    monkeypatch.setenv(
        "COMMONS_UCAN_TRUSTED_ISSUERS",
        json.dumps({did_key_from_public_key(issuer.public_bytes()): [resource]}),
    )
    payload["args"]["namespace"] = denied_namespace
    payload["att"] = [{"with": resource, "can": UCAN_COMMAND}]
    token = encode_ucan(issuer, payload)
    assert verify_ucan(token, changed.packet, signer_key_id=identity.key_id)
    decision = repository.submit(changed, identity, ucan=token)
    assert not decision.accepted
    assert any("namespace" in reason for reason in decision.reasons)
    assert not repository.objects_dir.exists()
    assert not (repository.root / "ledger.jsonl").exists()


def test_trusted_namespace_grant_admits_and_remains_idempotent(admission, identity):
    repository, signed, issuer, payload = admission
    token = encode_ucan(issuer, payload)
    assert repository.submit(signed, identity, ucan=token).accepted
    assert repository.submit(signed, identity, ucan=token).status == "already-present"
    assert repository.verify().ledger.blocks == 1


@pytest.mark.parametrize("configured", ["", "not-json", "null", "[]", "{}", "true"])
def test_invalid_trust_map_denies(admission, identity, monkeypatch, configured):
    repository, signed, issuer, payload = admission
    monkeypatch.setenv("COMMONS_UCAN_TRUSTED_ISSUERS", configured)
    _assert_denied_without_writes(repository, signed, identity, encode_ucan(issuer, payload))


@pytest.mark.parametrize("resources", [None, [], "commons://aafp-commons", [True], ["bogus"]])
def test_invalid_issuer_grants_deny(admission, identity, monkeypatch, resources):
    repository, signed, issuer, payload = admission
    monkeypatch.setenv(
        "COMMONS_UCAN_TRUSTED_ISSUERS",
        json.dumps(
            {
                did_key_from_public_key(issuer.public_bytes()): resources,
            }
        ),
    )
    _assert_denied_without_writes(repository, signed, identity, encode_ucan(issuer, payload))


@pytest.mark.parametrize("suffix", ["-other", "/child", "*"])
def test_namespace_grant_has_no_prefix_or_wildcard_authority(admission, identity, suffix):
    repository, signed, issuer, payload = admission
    # Including a valid capability must not mask another unauthorized grant.
    payload["att"].append({"with": payload["att"][0]["with"] + suffix, "can": UCAN_COMMAND})
    _assert_denied_without_writes(repository, signed, identity, encode_ucan(issuer, payload))


def test_trusted_grant_must_cover_actual_packet_namespace(admission, identity, monkeypatch):
    repository, signed, issuer, payload = admission
    other_resource = UCAN_NAMESPACE_PREFIX + "commons/different"
    monkeypatch.setenv(
        "COMMONS_UCAN_TRUSTED_ISSUERS",
        json.dumps(
            {
                did_key_from_public_key(issuer.public_bytes()): [other_resource],
            }
        ),
    )
    payload["att"] = [{"with": other_resource, "can": UCAN_COMMAND}]
    _assert_denied_without_writes(repository, signed, identity, encode_ucan(issuer, payload))


@pytest.mark.parametrize("constraint", ["signer", "namespace", "packet_id", "unknown", "caveat"])
def test_binding_and_constraint_failures_deny(admission, identity, constraint):
    repository, signed, issuer, payload = admission
    if constraint == "signer":
        del payload["args"]["signer_key_id"]
    elif constraint in {"namespace", "packet_id", "unknown"}:
        payload["args"][constraint] = "different-value"
    else:
        payload["att"][0]["nb"] = {"deny": True}
    _assert_denied_without_writes(repository, signed, identity, encode_ucan(issuer, payload))


def test_optional_mode_does_not_accept_untrusted_supplied_token(admission, identity, monkeypatch):
    repository, signed, _, payload = admission
    monkeypatch.delenv("COMMONS_REQUIRE_UCAN")
    token = encode_ucan(Identity.generate(), payload)
    _assert_denied_without_writes(repository, signed, identity, token)


def test_removing_issuer_trust_denies_next_submit_without_changing_history(
    admission, identity, monkeypatch
):
    repository, signed, issuer, payload = admission
    token = encode_ucan(issuer, payload)
    assert repository.submit(signed, identity, ucan=token).accepted
    original_ledger = (repository.root / "ledger.jsonl").read_bytes()
    monkeypatch.setenv("COMMONS_UCAN_TRUSTED_ISSUERS", "{}")
    another = sign_packet(
        replace(signed.packet, claim="A different evidence-backed claim."), identity
    )
    assert not repository.submit(another, identity, ucan=token).accepted
    assert (repository.root / "ledger.jsonl").read_bytes() == original_ledger
    assert [item.packet_id for item in repository.query()] == [signed.packet_id]
    assert repository.verify().valid  # Old admissions do not require current issuer trust.


def test_explicit_trust_configuration_overrides_environment(admission, monkeypatch):
    _, signed, issuer, payload = admission
    configured = {did_key_from_public_key(issuer.public_bytes()): [payload["att"][0]["with"]]}
    token = encode_ucan(issuer, payload)
    with pytest.raises(UcanError, match="trusted issuers"):
        verify_ucan(token, signed.packet, signer_key_id=signed.signer_key_id, trusted_issuers={})
    with pytest.raises(UcanError, match="audience"):
        verify_ucan(token, signed.packet, signer_key_id=signed.signer_key_id, expected_audience="")
    monkeypatch.delenv("COMMONS_UCAN_TRUSTED_ISSUERS")
    monkeypatch.delenv("COMMONS_UCAN_AUDIENCE")
    claims = verify_ucan(
        token,
        signed.packet,
        signer_key_id=signed.signer_key_id,
        trusted_issuers=configured,
        expected_audience=payload["aud"],
    )
    assert claims.issuer in configured


@pytest.mark.parametrize(
    "malformation", ["duplicate", "nan", "caveat", "header", "padding", "size"]
)
def test_ambiguous_or_unsupported_wire_tokens_deny(admission, identity, malformation):
    repository, signed, issuer, payload = admission
    header = {"alg": "EdDSA", "typ": "JWT"}
    raw = canonical_json({**payload, "iss": did_key_from_public_key(issuer.public_bytes())})
    if malformation == "duplicate":
        raw = b'{"aud":"unintended-audience",' + raw[1:]
    elif malformation == "nan":
        raw = b'{"nbf":NaN,' + raw[1:]
    elif malformation == "caveat":
        raw = b'{"fct":{"deny":true},' + raw[1:]
    elif malformation == "header":
        header["alg"] = "none"
    signing_input = f"{b64encode(canonical_json(header))}.{b64encode(raw)}"
    token = signing_input + "." + b64encode(issuer.sign(signing_input.encode("ascii")))
    if malformation == "padding":
        token += "="
    elif malformation == "size":
        token = "a" * 16_385
    _assert_denied_without_writes(repository, signed, identity, token)


def test_required_mode_preserves_source_reads_and_explicit_init(tmp_path, monkeypatch, capsys):
    home = tmp_path / "commons"
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("COMMONS_HOME", str(home))
    monkeypatch.setenv("COMMONS_REQUIRE_UCAN", "1")
    for variable in ("COMMONS_UCAN_AUDIENCE", "COMMONS_UCAN_TRUSTED_ISSUERS"):
        monkeypatch.delenv(variable, raising=False)
    assert main(["world"]) == 0
    assert json.loads(capsys.readouterr().out)["posture"] == "source"
    for tool, arguments in [("commons_world", {}), ("commons_get", {"packet_id": "absent"})]:
        _handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool, "arguments": arguments},
            },
            home,
        )
    assert not home.exists()
    assert not (tmp_path / ".commons").exists()
    assert main(["init"]) == 0
    assert home.exists()
    assert "COMMONS_UCAN_TRUSTED_ISSUERS" not in os.environ
    assert "COMMONS_UCAN_AUDIENCE" not in os.environ
