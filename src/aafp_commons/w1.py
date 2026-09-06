"""Installable W1 command surface for a local Commons node."""

from __future__ import annotations

import argparse
import json
import os
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

from ironclad.trust import Identity

from aafp_commons.canonical import b64decode, b64encode
from aafp_commons.constitutions import ConstitutionRef
from aafp_commons.identity import derive_agent_id
from aafp_commons.ledger import merkle_root
from aafp_commons.packages import default_registry
from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import SignedPacket

DEFAULT_CONSTITUTION = "grok-truth-seeking@1.0.0"
W1_VERSION = "0.1.0"


def home_path() -> Path:
    configured = os.environ.get("COMMONS_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".commons"


def _identity_path(home: Path) -> Path:
    return home / "identity.json"


def _constitution_path(home: Path) -> Path:
    return home / "constitution.json"


def _load_identity(home: Path) -> Identity | None:
    path = _identity_path(home)
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    return Identity.from_seed(b64decode(value["private_key_b64"]))


def _save_identity(home: Path, identity: Identity) -> None:
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
    )

    private_bytes = identity.private_key.private_bytes(
        encoding=Encoding.Raw,
        format=PrivateFormat.Raw,
        encryption_algorithm=NoEncryption(),
    )
    path = _identity_path(home)
    path.write_text(
        json.dumps(
            {
                "private_key_b64": b64encode(private_bytes),
                "public_key_b64": b64encode(identity.public_bytes()),
                "agent_id": derive_agent_id(identity.public_bytes()),
                "key_id": identity.key_id,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _load_constitution(home: Path) -> ConstitutionRef | None:
    path = _constitution_path(home)
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    return ConstitutionRef(
        constitution_id=value["constitution_id"],
        version=value["version"],
        digest=value.get("digest"),
    )


def _constitution_ref(text: str) -> tuple[str, str]:
    constitution_id, separator, version = text.partition("@")
    if not separator or not constitution_id or not version:
        raise ValueError("constitution must be formatted as ID@VERSION")
    return constitution_id, version


def _init(home: Path, selected: str) -> int:
    home.mkdir(parents=True, exist_ok=True)
    repository = CommonsRepository(home)
    repository.initialize()
    identity = _load_identity(home)
    if identity is None:
        identity = Identity.generate()
        _save_identity(home, identity)

    existing = _load_constitution(home)
    constitution_id, version = _constitution_ref(selected)
    package = default_registry().get(constitution_id, version)
    reference = repository.install_constitution(package.manifest)
    if existing is not None and existing != reference:
        raise ValueError("home is already initialized with a different constitution")
    _constitution_path(home).write_text(
        json.dumps(
            {
                "constitution_id": reference.constitution_id,
                "version": reference.version,
                "digest": reference.digest,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "home": str(home),
                "posture": "subject",
                "agent_id": derive_agent_id(identity.public_bytes()),
                "constitution": {
                    "constitution_id": reference.constitution_id,
                    "version": reference.version,
                    "digest": reference.digest,
                },
            },
            indent=2,
        )
    )
    return 0


def _packet_ids(home: Path) -> list[str]:
    objects = home / "objects"
    if not objects.exists():
        return []
    return [
        f"sha256:{path.stem}"
        for path in sorted(objects.glob("*.json"))
        if len(path.stem) == 64 and all(character in "0123456789abcdef" for character in path.stem)
    ]


RESOLUTION_NAMESPACE = "commons/sim/ml/resolution"
CONFLICT_NAMESPACE = "commons/sim/ml/conflict"


def _project_conflict_resolution_ids(root: Path) -> tuple[list[str], list[str]]:
    """Minimal deterministic projection of conflict_ids and resolution_ids.

    Scans stored packets for the ``commons/sim/ml/resolution`` and
    ``commons/sim/ml/conflict`` namespaces and extracts their IDs from the
    packet ``scope``. This reads from the same content-addressed object store
    — it does not invent a second ledger. Existing conflict IDs are preserved.
    """
    repository = CommonsRepository(root)
    if not repository.objects_dir.exists():
        return [], []
    conflict_ids: list[str] = []
    resolution_ids: list[str] = []
    for signed in repository.query(""):
        scope = signed.packet.scope
        if signed.packet.namespace == RESOLUTION_NAMESPACE:
            rid = scope.get("resolution_id")
            if isinstance(rid, str) and rid not in resolution_ids:
                resolution_ids.append(rid)
        elif signed.packet.namespace == CONFLICT_NAMESPACE:
            cid = scope.get("conflict_id")
            if isinstance(cid, str) and cid not in conflict_ids:
                conflict_ids.append(cid)
    return sorted(conflict_ids), sorted(resolution_ids)


def _project_review_queue(root: Path) -> list[dict[str, Any]]:
    repository = CommonsRepository(root)
    if not repository.objects_dir.exists():
        return []
    reviewed: set[str] = set()
    claims: list[dict[str, Any]] = []
    for signed in repository.query(""):
        if signed.packet.namespace == "commons/review/result":
            claim_id = signed.packet.scope.get("claim_id")
            if (
                signed.packet.scope.get("decision") in {
                "accept-display", "need-evidence", "reject-spam", "reject-scope",
                "reject-constitution", "conflict", "escalate",
                }
                and isinstance(claim_id, str)
            ):
                reviewed.add(claim_id)
        elif signed.packet.namespace != "commons/review/result":
            claims.append({"claim_id": signed.packet_id, "enqueued_at": signed.packet.created_at})
    now = int(time.time())
    return [
        {
            **claim,
            "state": "in-review",
            "reviewer_subject": None,
            "last_transition_at": now,
        }
        for claim in claims
        if claim["claim_id"] not in reviewed
    ]


def world(home: Path | None = None) -> dict[str, Any]:
    root = home or home_path()
    identity = _load_identity(root)
    reference = _load_constitution(root)
    repository = CommonsRepository(root)
    blocks = repository.ledger.blocks()
    packet_ids = _packet_ids(root)
    conflict_ids, resolution_ids = _project_conflict_resolution_ids(root)
    constitution: dict[str, str | None] | None = None
    if reference is not None:
        constitution = {
            "constitution_id": reference.constitution_id,
            "version": reference.version,
            "digest": reference.digest,
        }
    return {
        "packet_set_merkle": merkle_root(packet_ids),
        "local_tip": blocks[-1].block.block_hash if blocks else "",
        "peer_tips": {},
        "fork_ids": [],
        "conflict_ids": conflict_ids,
        "resolution_ids": resolution_ids,
        "packet_count": len(packet_ids),
        "posture": "subject" if identity is not None else "source",
        "agent_id": derive_agent_id(identity.public_bytes()) if identity else None,
        "constitution": constitution,
        "review_queue": _project_review_queue(root),
    }


def _print_world(home: Path) -> int:
    print(json.dumps(world(home), indent=2, sort_keys=True))
    return 0


def _get(home: Path, packet_id: str) -> int:
    try:
        packet = CommonsRepository(home).get(packet_id)
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error)}))
        return 1
    print(json.dumps(packet.to_dict(), indent=2, sort_keys=True))
    return 0


def _packet_export(home: Path) -> dict[str, Any]:
    packets = CommonsRepository(home).query("")
    return {"packets": [packet.to_dict() for packet in packets]}


def _loopback_peer(peer: str) -> str:
    parsed = urlparse(peer)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1"}:
        raise ValueError("replication peer must be an http loopback URL")
    return peer.rstrip("/") + "/packets"


def _replicate(home: Path, peer: str) -> dict[str, Any]:
    identity = _load_identity(home)
    if identity is None:
        raise ValueError("INIT_REQUIRED: initialize this home before replication")
    with urlopen(_loopback_peer(peer), timeout=5) as response:
        payload = json.load(response)
    exported = payload.get("packets") if isinstance(payload, dict) else None
    if not isinstance(exported, list):
        raise ValueError("peer packet export must contain a packets list")

    repository = CommonsRepository(home)
    accepted = 0
    already_present = 0
    for value in exported:
        if not isinstance(value, dict):
            raise ValueError("peer packet export contains a non-object packet")
        decision = repository.submit(SignedPacket.from_dict(value), identity)
        if not decision.accepted:
            raise ValueError("packet rejected during replication: " + "; ".join(decision.reasons))
        if decision.status == "already-present":
            already_present += 1
        else:
            accepted += 1
    return {"accepted": accepted, "already_present": already_present, "packet_count": len(exported)}


class _WorldServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def _handler(home: Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/world":
                payload = json.dumps(world(home), sort_keys=True).encode("utf-8")
            elif self.path == "/packets":
                payload = json.dumps(_packet_export(home), sort_keys=True).encode("utf-8")
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/replicate":
                self.send_response(404)
                self.end_headers()
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                request = json.loads(self.rfile.read(length).decode("utf-8"))
                peer = request.get("peer") if isinstance(request, dict) else None
                if not isinstance(peer, str):
                    raise ValueError("replicate requires a peer URL")
                result = {"ok": True, **_replicate(home, peer)}
                status = 200
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                result = {"ok": False, "error": str(error)}
                status = 400
            payload = json.dumps(result, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    return Handler


def _serve(home: Path, port: int) -> int:
    home.mkdir(parents=True, exist_ok=True)
    pid_path = home / "node.pid"
    if pid_path.exists():
        try:
            os.kill(int(pid_path.read_text(encoding="utf-8")), 0)
        except (OSError, ValueError):
            pid_path.unlink(missing_ok=True)
        else:
            raise ValueError(f"a Commons server is already running for {home}")

    server = _WorldServer(("127.0.0.1", port), _handler(home))
    pid_path.write_text(str(os.getpid()), encoding="utf-8")

    def stop(_signum: int, _frame: Any) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    print(f"commons serve home={home} bind=127.0.0.1:{port}", flush=True)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()
        pid_path.unlink(missing_ok=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="commons",
        description="Commons is a local signed notebook other agents can replicate.",
    )
    commands = parser.add_subparsers(dest="command")
    init = commands.add_parser("init", help="create a signing subject and local home")
    init.add_argument("--constitution", default=DEFAULT_CONSTITUTION, metavar="ID@VERSION")
    serve = commands.add_parser("serve", help="serve the local world on loopback")
    serve.add_argument("--port", type=int, default=8081)
    commands.add_parser("world", help="print the local world")
    get = commands.add_parser("get", help="read one packet by content address")
    get.add_argument("packet_id")
    commands.add_parser("mcp", help="run the zero-config stdio MCP server")
    evidence = commands.add_parser("evidence", help="local evidence bundles")
    evidence_commands = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_pack = evidence_commands.add_parser("pack", help="pack claim evidence")
    evidence_pack.add_argument("claim_id")
    evidence_pack.add_argument("--out", type=Path, required=True)
    evidence_check = evidence_commands.add_parser("check", help="check bundle digests")
    evidence_check.add_argument("bundle", type=Path)
    verify = commands.add_parser("verify", help="record a local verification result")
    verify.add_argument("claim_id")
    verify.add_argument("--method", required=True)
    status = commands.add_parser("status", help="show local claim verification status")
    status.add_argument("claim_id")
    rely_cmd = commands.add_parser("rely", help="evaluate rely decision for a claim")
    rely_cmd.add_argument("claim_id")
    review = commands.add_parser("review", help="local signed claim review")
    review_commands = review.add_subparsers(dest="review_command", required=True)
    enqueue = review_commands.add_parser("enqueue", help="enqueue a claim for review")
    enqueue.add_argument("claim_id")
    enqueue.add_argument("--reviewer-subject")
    decide = review_commands.add_parser("decide", help="record a signed review result")
    decide.add_argument("claim_id")
    decide.add_argument("--decision", required=True)
    decide.add_argument("--bundle-id")
    resolve_cmd = commands.add_parser("resolve", help="write an explicit local conflict resolution")
    resolve_cmd.add_argument("claim_id")
    resolve_cmd.add_argument("--prefer", required=True)
    resolve_cmd.add_argument("--rationale", required=True)
    policy = commands.add_parser("policy", help="show or update local rely policy")
    policy_commands = policy.add_subparsers(dest="policy_command", required=True)
    policy_commands.add_parser("show")
    policy_set = policy_commands.add_parser("set")
    policy_set.add_argument("--accept-resolution", action="store_true")
    policy_set.add_argument("--mode", choices=("display", "consequential"), default="display")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    home = home_path()
    try:
        if args.command is None:
            state = world(home)
            print(
                f"commons {W1_VERSION} home={home} posture={state['posture']} "
                f"height={state['packet_count']}"
            )
            print("\n  commons init     create a signing subject")
            print("  commons serve    serve /world on loopback")
            print("  commons world    print the local world")
            print("  commons get ID   read one packet")
            return 0
        if args.command == "init":
            return _init(home, args.constitution)
        if args.command == "serve":
            return _serve(home, args.port)
        if args.command == "world":
            return _print_world(home)
        if args.command == "get":
            return _get(home, args.packet_id)
        if args.command == "mcp":
            from aafp_commons.mcp_stdio import serve_stdio

            return serve_stdio(home=home)
        if args.command == "evidence":
            from aafp_commons.verification import check_bundle, pack_evidence

            if args.evidence_command == "pack":
                identity = _load_identity(home)
                value = pack_evidence(CommonsRepository(home), args.claim_id, args.out, identity)
                print(json.dumps({"evidence_id": value["evidence_id"], "output": str(args.out),
                                  "missing": value["missing"]}, indent=2))
                return 0
            value = check_bundle(args.bundle)
            print(json.dumps({"evidence_id": value.get("evidence_id"),
                              "digest_checked": value["digest_checked"],
                              "checks": value["checks"]}, indent=2))
            return 0 if value["digest_checked"] else 1
        if args.command == "verify":
            from aafp_commons.verification import record_verification

            identity = _load_identity(home)
            verifier_agent_id = (
                derive_agent_id(identity.public_bytes()) if identity else "local-verifier"
            )
            print(json.dumps(record_verification(home, args.claim_id, args.method,
                                                 verifier_agent_id, "unavailable", identity),
                             indent=2))
            return 0
        if args.command == "status":
            from aafp_commons.verification import status

            print(json.dumps(status(CommonsRepository(home), args.claim_id), indent=2))
            return 0
        if args.command == "rely":
            from aafp_commons.verification import rely

            print(json.dumps(rely(CommonsRepository(home), args.claim_id), indent=2))
            return 0
        if args.command == "review":
            from aafp_commons.review import decide as decide_review
            from aafp_commons.review import queue

            repository = CommonsRepository(home)
            if args.review_command == "enqueue":
                print(json.dumps(queue(repository, args.claim_id, args.reviewer_subject), indent=2))
                return 0
            identity = _load_identity(home)
            reference = _load_constitution(home)
            if identity is None or reference is None:
                raise ValueError("INIT_REQUIRED: review decisions require an initialized home")
            constitution = repository.constitutions.resolve(reference)
            print(json.dumps(decide_review(
                repository, args.claim_id, identity, constitution,
                args.decision, args.bundle_id,
            ), indent=2))
            return 0
        if args.command == "resolve":
            from aafp_commons.conflicts import resolve
            identity = _load_identity(home)
            reference = _load_constitution(home)
            if identity is None or reference is None:
                raise ValueError("INIT_REQUIRED: resolutions require an initialized home")
            repository = CommonsRepository(home)
            constitution = repository.constitutions.resolve(reference)
            print(json.dumps(resolve(repository, args.claim_id, identity, constitution,
                                      args.prefer, args.rationale), indent=2))
            return 0
        if args.command == "policy":
            from aafp_commons.verification import DEFAULT_RELY_POLICY, load_rely_policy
            path = home / "policy.rely.json"
            if args.policy_command == "show":
                print(json.dumps(load_rely_policy(home), indent=2, sort_keys=True))
                return 0
            value = load_rely_policy(home) if path.exists() else dict(DEFAULT_RELY_POLICY)
            value["accept_resolution"] = args.accept_resolution
            value["mode"] = args.mode
            path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps(value, indent=2, sort_keys=True))
            return 0
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error)}))
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
