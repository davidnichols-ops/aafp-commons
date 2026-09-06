"""Small dependency-free stdio MCP server for Commons W2."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, BinaryIO

from aafp_commons.constitutions import ConstitutionError
from aafp_commons.identity import derive_agent_id
from aafp_commons.models import EvidenceRef, KnowledgePacket, MethodRef
from aafp_commons.repository import CommonsRepository
from aafp_commons.signing import sign_packet
from aafp_commons.w1 import _load_constitution, _load_identity, home_path, world

PROTOCOL_VERSION = "2025-06-18"

TOOL_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "name": "commons_world",
        "description": (
            "Read the local signed world. This is safe in source posture; writing requires "
            "an initialized subject, evidence, and a digest-pinned constitution."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "commons_query",
        "description": (
            "Query exact packet IDs or scan a namespace prefix. An empty query scans every "
            "admitted namespace (commons/, org/, and agent/). Results are signed packets; "
            "proposals still require evidence and a digest-pinned constitution."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "commons_get",
        "description": (
            "Read one signed packet by content address. Writing requires evidence and a "
            "digest-pinned constitution."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"packet_id": {"type": "string"}},
            "required": ["packet_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "commons_assume_constitution",
        "description": (
            "Validate the constitution selected by commons init. Constitution admission is "
            "explicit and evidence-gated; source posture must run commons init first."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "commons_propose",
        "description": (
            "Sign and admit one packet. Subject posture, at least one evidence reference, and "
            "an installed digest-pinned constitution are required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string"},
                "namespace": {"type": "string"},
                "claim": {"type": "string"},
                "scope": {"type": "object"},
                "evidence": {"type": "array", "items": {"type": "object"}},
                "confidence": {"type": "number"},
                "author_agent_id": {"type": "string"},
                "method": {"type": "object"},
                "visibility": {"type": "string"},
                "license": {"type": "string"},
                "ucan": {"type": "string"},
            },
            "required": ["namespace", "claim", "evidence"],
            "additionalProperties": False,
        },
    },
    {
        "name": "commons_conflicts",
        "description": (
            "Read conflict IDs in the local world. Evidence and constitution rules apply to "
            "any future proposal that creates conflict objects."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "commons_resolutions",
        "description": (
            "Read resolution IDs in the local world. Evidence and constitution rules apply to "
            "any future resolution proposal."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
)


def _error(code: str, message: str, **details: Any) -> tuple[dict[str, Any], bool]:
    payload: dict[str, Any] = {"ok": False, "error": {"code": code, "message": message}}
    if details:
        payload["error"].update(details)
    return payload, True


def _ok(**values: Any) -> tuple[dict[str, Any], bool]:
    return {"ok": True, **values}, False


def _query(home: Path, query: str | None) -> tuple[dict[str, Any], bool]:
    repository = CommonsRepository(home)
    try:
        if query and query.startswith("sha256:"):
            packets = [repository.get(query)]
            prefix = query
        else:
            prefix = query or ""
            packets = repository.query(prefix)
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return _error("QUERY_INVALID", str(error))
    return _ok(namespace_prefix=prefix, results=[packet.to_dict() for packet in packets])


def _get(home: Path, packet_id: str) -> tuple[dict[str, Any], bool]:
    try:
        packet = CommonsRepository(home).get(packet_id)
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return _error("PACKET_NOT_FOUND", str(error), packet_id=packet_id)
    return _ok(packet=packet.to_dict())


def _assume_constitution(home: Path) -> tuple[dict[str, Any], bool]:
    identity = _load_identity(home)
    if identity is None:
        return _error(
            "INIT_REQUIRED",
            "source posture cannot assume a constitution; run commons init first",
        )
    reference = _load_constitution(home)
    if reference is None:
        return _error("CONSTITUTION_REQUIRED", "commons init did not select a constitution")
    try:
        CommonsRepository(home).constitutions.resolve(reference)
    except ConstitutionError as error:
        return _error("CONSTITUTION_INVALID", str(error))
    return _ok(
        posture="subject",
        agent_id=derive_agent_id(identity.public_bytes()),
        constitution=asdict(reference),
    )


def _propose(home: Path, arguments: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    identity = _load_identity(home)
    if identity is None:
        return _error(
            "SOURCE_POSTURE",
            "source posture is read-only; run commons init before proposing",
        )
    reference = _load_constitution(home)
    if reference is None:
        return _error("CONSTITUTION_REQUIRED", "commons init did not select a constitution")
    try:
        evidence = tuple(EvidenceRef(**item) for item in arguments.get("evidence", ()))
        method_value = arguments.get("method") or {"name": "commons-mcp", "version": "1.0"}
        packet = KnowledgePacket(
            kind=arguments.get("kind", "finding"),
            namespace=arguments["namespace"],
            claim=arguments["claim"],
            scope=arguments.get("scope", {}),
            evidence=evidence,
            confidence=arguments.get("confidence", 0.5),
            author_agent_id=arguments.get(
                "author_agent_id", derive_agent_id(identity.public_bytes())
            ),
            constitution=reference,
            method=MethodRef(**method_value),
            visibility=arguments.get("visibility", "public"),
            license=arguments.get("license", "commons-v1"),
        )
        signed = sign_packet(packet, identity)
        decision = CommonsRepository(home).submit(signed, identity, ucan=arguments.get("ucan"))
    except (KeyError, TypeError, ValueError, ConstitutionError) as error:
        return _error("INVALID_PACKET", str(error))
    if not decision.accepted:
        if any(reason.startswith("UCAN_REQUIRED") for reason in decision.reasons):
            return _error("UCAN_REQUIRED", "submit requires a UCAN")
        if any(reason.startswith("UCAN_INVALID") for reason in decision.reasons):
            return _error("UCAN_INVALID", "UCAN admission failed", reasons=list(decision.reasons))
        return _error(
            "ADMISSION_REJECTED",
            "constitution or policy rejected the packet",
            reasons=list(decision.reasons),
        )
    return _ok(packet_id=signed.packet_id, status=decision.status)


def _call_tool(home: Path, name: str, arguments: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    if name == "commons_world":
        return _ok(world=world(home))
    if name == "commons_query":
        return _query(home, arguments.get("query"))
    if name == "commons_get":
        packet_id = arguments.get("packet_id")
        if not isinstance(packet_id, str):
            return _error("INVALID_ARGUMENTS", "packet_id must be a string")
        return _get(home, packet_id)
    if name == "commons_assume_constitution":
        return _assume_constitution(home)
    if name == "commons_propose":
        return _propose(home, arguments)
    if name == "commons_conflicts":
        return _ok(conflict_ids=world(home)["conflict_ids"])
    if name == "commons_resolutions":
        return _ok(resolution_ids=world(home)["resolution_ids"])
    return _error("UNKNOWN_TOOL", f"unknown Commons tool: {name}")


def _response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _handle(request: dict[str, Any], home: Path) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return _response(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "commons", "version": "0.1.0"},
                "instructions": (
                    "Commons is a local signed notebook. Read in source posture; write only "
                    "as a subject under an evidence-gated constitution."
                ),
            },
        )
    if method == "tools/list":
        return _response(request_id, {"tools": list(TOOL_DEFINITIONS)})
    if method == "tools/call":
        params = request.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return _rpc_error(request_id, -32602, "tools/call requires name and object arguments")
        payload, is_error = _call_tool(home, name, arguments)
        return _response(
            request_id,
            {
                "content": [{"type": "text", "text": json.dumps(payload, sort_keys=True)}],
                "structuredContent": payload,
                "isError": is_error,
            },
        )
    return _rpc_error(request_id, -32601, f"method not found: {method}")


def _read_message(stream: BinaryIO) -> tuple[dict[str, Any] | None, str]:
    first = stream.readline()
    if not first:
        return None, "line"
    while first in (b"\n", b"\r\n"):
        first = stream.readline()
        if not first:
            return None, "line"
    if first.lower().startswith(b"content-length:"):
        headers = [first]
        while True:
            line = stream.readline()
            if not line or line in (b"\n", b"\r\n"):
                break
            headers.append(line)
        length = next(
            int(header.split(b":", 1)[1].strip())
            for header in headers
            if header.lower().startswith(b"content-length:")
        )
        body = stream.read(length)
        return json.loads(body.decode("utf-8")), "framed"
    return json.loads(first.decode("utf-8")), "line"


def _write_message(stream: BinaryIO, value: dict[str, Any], mode: str) -> None:
    encoded = json.dumps(value, separators=(",", ":")).encode("utf-8")
    if mode == "framed":
        stream.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("ascii"))
        stream.write(encoded)
    else:
        stream.write(encoded + b"\n")
    stream.flush()


def serve_stdio(
    input_stream: BinaryIO | None = None,
    output_stream: BinaryIO | None = None,
    home: Path | None = None,
) -> int:
    source = input_stream or sys.stdin.buffer
    destination = output_stream or sys.stdout.buffer
    root = home or home_path()
    while True:
        try:
            request, mode = _read_message(source)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            _write_message(destination, _rpc_error(None, -32700, str(error)), "line")
            continue
        if request is None:
            return 0
        response = _handle(request, root)
        if response is not None:
            _write_message(destination, response, mode)
