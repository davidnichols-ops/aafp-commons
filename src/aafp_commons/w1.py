"""Installable W1 command surface for a local Commons node."""

from __future__ import annotations

import argparse
import json
import os
import signal
import threading
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


def world(home: Path | None = None) -> dict[str, Any]:
    root = home or home_path()
    identity = _load_identity(root)
    reference = _load_constitution(root)
    repository = CommonsRepository(root)
    blocks = repository.ledger.blocks()
    packet_ids = _packet_ids(root)
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
        "conflict_ids": [],
        "resolution_ids": [],
        "packet_count": len(packet_ids),
        "posture": "subject" if identity is not None else "source",
        "agent_id": derive_agent_id(identity.public_bytes()) if identity else None,
        "constitution": constitution,
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
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error)}))
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
