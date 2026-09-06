"""Local evidence bundles, verification results, and rely status.

This plane is deliberately local: it records and checks bytes, never resolves
evidence URIs during reads, and keeps admission separate from support.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from ironclad.canon import content_digest
from ironclad.trust import Identity

from aafp_commons.canonical import b64decode, b64encode, canonical_json, digest
from aafp_commons.repository import CommonsRepository

Outcome = Literal["digest_checked", "reproduced", "supported", "failed", "unavailable"]
DISCLOSURES = {"public", "redacted", "private"}
OUTCOMES = {"digest_checked", "reproduced", "supported", "failed", "unavailable"}
STATUS_FIELDS = ("evidence_supplied", "digest_checked", "reproduced", "supported")
_PRIVATE_REF = re.compile(r"(?:^|/)(?:Users|home|private|tmp|var)/|(?:https?|ssh)://", re.I)

# Fields that are part of the signature envelope, not the content.  Content IDs
# and signed payloads always exclude these so that a signature is stable across
# serialisation and does not sign itself.
_SIGNATURE_FIELDS = ("signer_key_id", "signature_b64", "signer_public_key_b64")


class VerificationError(ValueError):
    """Raised for malformed or unsafe local verification data."""


@dataclass(frozen=True)
class EvidenceFile:
    path_rel: str
    sha256: str
    bytes: str | None = None
    absent: bool = False


@dataclass(frozen=True)
class EvidenceBundle:
    claim_ids: tuple[str, ...]
    files: tuple[EvidenceFile, ...]
    disclosure: str
    source_transform: dict[str, Any] | None = None
    missing: tuple[str, ...] = ()
    evidence_id: str = ""
    signer_key_id: str | None = None
    signature_b64: str | None = None
    signer_public_key_b64: str | None = None

    def __post_init__(self) -> None:
        if self.disclosure not in DISCLOSURES:
            raise VerificationError("invalid evidence disclosure")
        if not self.claim_ids:
            raise VerificationError("evidence bundle requires a claim")
        if any(not item.path_rel or Path(item.path_rel).is_absolute() for item in self.files):
            raise VerificationError("evidence paths must be relative")
        if self.disclosure == "redacted" and not self.source_transform:
            raise VerificationError("redacted evidence requires source_transform")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["claim_ids"] = list(self.claim_ids)
        value["files"] = [asdict(item) for item in self.files]
        value["missing"] = list(self.missing)
        value["evidence_id"] = self.evidence_id or evidence_id(value)
        return value


@dataclass(frozen=True)
class VerificationResult:
    claim_id: str
    evidence_digests: tuple[str, ...]
    method_id: str
    outcome: str
    limitations: tuple[str, ...]
    verifier_agent_id: str
    policy_id: str
    verification_id: str = ""
    signer_key_id: str | None = None
    signature_b64: str | None = None
    signer_public_key_b64: str | None = None

    def __post_init__(self) -> None:
        if self.outcome not in OUTCOMES:
            raise VerificationError("invalid verification outcome")
        if not self.claim_id or not self.method_id or not self.verifier_agent_id:
            raise VerificationError("verification result identifiers are required")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_digests"] = list(self.evidence_digests)
        value["limitations"] = list(self.limitations)
        value["verification_id"] = self.verification_id or verification_id(value)
        return value


def evidence_id(value: dict[str, Any]) -> str:
    body = dict(value)
    body.pop("evidence_id", None)
    for field in _SIGNATURE_FIELDS:
        body.pop(field, None)
    return digest(body)


def verification_id(value: dict[str, Any]) -> str:
    body = dict(value)
    body.pop("verification_id", None)
    for field in _SIGNATURE_FIELDS:
        body.pop(field, None)
    return digest(body)


_SIGNING_DOMAIN = b"aafp-commons/verification/v0\x00"


def _signed_payload(value: dict[str, Any]) -> dict[str, Any]:
    body = dict(value)
    for field in _SIGNATURE_FIELDS:
        body.pop(field, None)
    return body


def _key_id_for_public_key(public_bytes: bytes) -> str:
    return content_digest({"ed25519_pub_b64": b64encode(public_bytes)})


def sign_object(value: dict[str, Any], identity: Identity) -> dict[str, Any]:
    body = _signed_payload(value)
    body.pop("evidence_id", None)
    body.pop("verification_id", None)
    if "claim_ids" in body:
        body["evidence_id"] = evidence_id(body)
    else:
        body["verification_id"] = verification_id(body)
    encoded = canonical_json(body)
    body["signer_key_id"] = identity.key_id
    body["signer_public_key_b64"] = b64encode(identity.public_bytes())
    body["signature_b64"] = b64encode(identity.sign(_SIGNING_DOMAIN + encoded))
    return body


def verify_object(value: dict[str, Any]) -> bool:
    """Verify a signed EvidenceBundle or VerificationResult in-place.

    Direct verification is possible from the signed payload alone: the public
    key travels with the object (``signer_public_key_b64``), the ``signer_key_id``
    is re-derived from it, and the signature covers the canonical content
    excluding all signature-envelope fields.  No second key format or external
    registry is involved.
    """
    try:
        signature = value.get("signature_b64")
        key_id = value.get("signer_key_id")
        public_key_b64 = value.get("signer_public_key_b64")
        if not isinstance(signature, str) or not isinstance(key_id, str):
            return False
        if not isinstance(public_key_b64, str):
            return False
        public_bytes = b64decode(public_key_b64)
        if _key_id_for_public_key(public_bytes) != key_id:
            return False
        public_key = Ed25519PublicKey.from_public_bytes(public_bytes)
        body = _signed_payload(value)
        encoded = canonical_json(body)
        public_key.verify(b64decode(signature), _SIGNING_DOMAIN + encoded)
        # Defence in depth: recompute the content ID and confirm it matches.
        if "claim_ids" in body:
            if body.get("evidence_id") != evidence_id(body):
                return False
        else:
            if body.get("verification_id") != verification_id(body):
                return False
        return True
    except Exception:  # cryptographic verification fails closed
        return False


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def pack_evidence(
    repository: CommonsRepository, claim_id: str, output: Path, identity: Identity | None = None
) -> dict[str, Any]:
    signed = repository.get(claim_id)
    files: list[EvidenceFile] = []
    missing: list[str] = []
    for reference in signed.packet.evidence:
        uri = reference.uri
        candidate = Path(uri)
        if candidate.is_absolute() or not candidate.exists() or not candidate.is_file():
            missing.append(uri)
            continue
        files.append(EvidenceFile(uri, _sha256(candidate), candidate.read_bytes().hex()))
    bundle = EvidenceBundle(
        claim_ids=(claim_id,), files=tuple(files), disclosure="private", missing=tuple(missing)
    ).to_dict()
    if identity is not None:
        bundle = sign_object(bundle, identity)
    output.write_text(json.dumps(bundle, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return bundle


def check_bundle(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    files = value.get("files", [])
    results: list[dict[str, Any]] = []
    for item in files:
        raw = bytes.fromhex(item["bytes"]) if item.get("bytes") is not None else None
        actual = "sha256:" + hashlib.sha256(raw).hexdigest() if raw is not None else None
        results.append({"path_rel": item.get("path_rel"), "ok": actual == item.get("sha256")})
    value["digest_checked"] = all(item["ok"] for item in results) and not value.get("missing")
    value["checks"] = results
    return value


DEFAULT_RELY_POLICY: dict[str, Any] = {
    "trusted_verifiers": [],
    "allow_same_operator": False,
}


def load_rely_policy(home: str | Path) -> dict[str, Any]:
    """Load rely policy from ``COMMONS_HOME/policy.rely.json``.

    Returns the default policy when the file is absent. The default rejects
    same-operator verification and has no trusted verifiers.
    """
    path = Path(home) / "policy.rely.json"
    if not path.exists():
        return dict(DEFAULT_RELY_POLICY)
    value = json.loads(path.read_text(encoding="utf-8"))
    return {
        "trusted_verifiers": list(value.get("trusted_verifiers", [])),
        "allow_same_operator": bool(value.get("allow_same_operator", False)),
    }


def _is_trusted_verifier(result: dict[str, Any], policy: dict[str, Any]) -> bool:
    if not verify_object(result):
        return False
    trusted = policy.get("trusted_verifiers", [])
    verifier_id = result.get("verifier_agent_id", "")
    return verifier_id in trusted


def _consequential_ok(
    results: list[dict[str, Any]],
    signer_agent_id: str | None,
    policy: dict[str, Any],
) -> bool:
    """Consequential rely: reproduced OR supported from a trusted verifier.

    Same-operator verification is rejected unless ``allow_same_operator`` is
    true.  Only signed results count — an unsigned claim of reproduction or
    support is not consequential evidence.
    """
    allow_same = policy.get("allow_same_operator", False)
    trusted = policy.get("trusted_verifiers", [])
    for item in results:
        if not verify_object(item):
            continue
        outcome = item.get("outcome")
        verifier_id = item.get("verifier_agent_id", "")
        is_reproduced = outcome == "reproduced" and verifier_id in trusted
        is_supported_trusted = outcome == "supported" and verifier_id in trusted
        if not (is_reproduced or is_supported_trusted):
            continue
        is_same_operator = verifier_id == signer_agent_id
        if is_same_operator and not allow_same:
            continue
        return True
    return False


def status(
    repository: CommonsRepository,
    claim_id: str,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    signed = repository.get(claim_id)
    supplied = bool(signed.packet.evidence)
    results = _results(repository.root, claim_id)
    checked = any(item["outcome"] == "digest_checked" for item in results)
    reproduced = any(item["outcome"] == "reproduced" for item in results)
    supported = any(item["outcome"] == "supported" for item in results)
    verifier_signed = any(verify_object(item) for item in results)
    signer_agent_id = signed.packet.author_agent_id
    independent = any(
        item.get("verifier_agent_id") != signer_agent_id and verify_object(item)
        for item in results
    )
    if policy is None:
        policy = load_rely_policy(repository.root)
    rely_ok = _consequential_ok(results, signer_agent_id, policy)
    return {
        "claim_id": claim_id,
        "evidence_supplied": supplied,
        "digest_checked": checked,
        "reproduced": reproduced,
        "supported": supported,
        "verifier_signed": verifier_signed,
        "independent_corroboration": independent,
        "rely_ok": rely_ok,
    }


def rely(
    repository: CommonsRepository,
    claim_id: str,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate a rely decision for a claim without writing anything.

    ``display`` requires only ``evidence_supplied``.  ``consequential`` requires
    reproduced OR supported from a trusted verifier, rejecting same-operator
    verification unless ``allow_same_operator`` is true.  This command never
    auto-writes a rely record — it is an explicit evaluation only.
    """
    if policy is None:
        policy = load_rely_policy(repository.root)
    status_value = status(repository, claim_id, policy)
    return {
        "claim_id": claim_id,
        "display": status_value["evidence_supplied"],
        "consequential": status_value["rely_ok"],
        "rely_ok": status_value["rely_ok"],
        "status": status_value,
    }


def record_verification(
    root: Path, claim_id: str, method_id: str, verifier_agent_id: str, outcome: Outcome,
    identity: Identity | None = None,
) -> dict[str, Any]:
    result = VerificationResult(
        claim_id=claim_id, evidence_digests=(), method_id=method_id, outcome=outcome,
        limitations=(), verifier_agent_id=verifier_agent_id, policy_id="local-v0",
    ).to_dict()
    if identity is not None:
        result = sign_object(result, identity)
    path = root / "verification" / f"{result['verification_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return result


def _results(root: Path, claim_id: str) -> list[dict[str, Any]]:
    directory = root / "verification"
    if not directory.exists():
        return []
    return [
        value for path in sorted(directory.glob("*.json"))
        if (value := json.loads(path.read_text(encoding="utf-8"))).get("claim_id") == claim_id
    ]


def export_safe(value: dict[str, Any]) -> dict[str, Any]:
    """Reject private locators unless a distinct redacted artifact is recorded."""
    if (
        _PRIVATE_REF.search(json.dumps(value, sort_keys=True))
        and (value.get("disclosure") != "redacted" or not value.get("source_transform"))
    ):
        raise VerificationError("private evidence reference requires redaction before export")
    return value
