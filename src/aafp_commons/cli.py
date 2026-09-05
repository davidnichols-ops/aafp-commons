"""Small operator CLI for the first local commons node."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ironclad.trust import Identity

from aafp_commons.adoption import ADOPTION_BOUNDARY
from aafp_commons.constitutions import ConstitutionManifest, FileConstitutionResolver
from aafp_commons.discovery import ConstitutionCatalog
from aafp_commons.handshake import HANDSHAKE_BOUNDARY, RuntimeHandshake
from aafp_commons.identity import derive_agent_id
from aafp_commons.index import PublicResearchIndex
from aafp_commons.join import AgentJoinSession
from aafp_commons.models import ConstitutionRef, EvidenceRef, KnowledgePacket, MethodRef
from aafp_commons.packages import (
    ConstitutionPackage,
    ConstitutionPackageNotFoundError,
    default_registry,
)
from aafp_commons.protocols import load_schema, protocol_ids
from aafp_commons.providers.grokipedia import DEFAULT_BASE_URL, GrokipediaProvider
from aafp_commons.repository import CommonsRepository
from aafp_commons.sharing import (
    export_public_snapshot,
    load_public_snapshot,
    search_public_snapshot,
)
from aafp_commons.signing import sign_packet

CATALOG_SCHEMA = "aafp.commons/constitution-catalog@1"
SELECTION_SCHEMA = "aafp.commons/constitution-selection@1"
INSTALLATION_SCHEMA = "aafp.commons/constitution-installation@1"


def _demo(root: Path) -> int:
    signer = Identity.generate()
    # Deliberately distinct from the Ironclad signing key. Production callers
    # resolve this public key from a verified AAFP AgentRecord.
    author_agent_id = derive_agent_id(b"demo-aafp-agent-public-key")
    constitution = ConstitutionManifest(
        constitution_id="frontier-dev",
        version="0.1",
        namespace_prefixes=("commons/frontend",),
    )
    packet = KnowledgePacket(
        kind="observation",
        namespace="commons/frontend/react",
        claim=(
            "Repeated hydration failures were resolved by comparing server and client "
            "inputs first."
        ),
        scope={"framework": "react", "failure": "hydration-mismatch"},
        evidence=(EvidenceRef(kind="reproduction", uri="local://demo/hydration-run-1"),),
        confidence=0.72,
        author_agent_id=author_agent_id,
        constitution=constitution.ref,
        method=MethodRef("controlled-debugging-run", "0.1"),
    )
    repository = CommonsRepository(root)
    repository.install_constitution(constitution)
    decision = repository.submit(sign_packet(packet, signer), signer)
    result = repository.verify()
    print(
        json.dumps(
            {
                "packet_id": packet.packet_id,
                "admission": decision.status,
                "repository_valid": result.valid,
                "blocks": result.ledger.blocks,
            },
            indent=2,
        )
    )
    return 0 if result.valid else 1


def _verify(root: Path) -> int:
    result = CommonsRepository(root).verify()
    print(json.dumps({
        "valid": result.valid,
        "objects": result.objects,
        "blocks": result.ledger.blocks,
        "packets": result.ledger.packets,
        "errors": result.errors,
    }, indent=2))
    return 0 if result.valid else 1


def _grokipedia(topic: str, base_url: str) -> int:
    document = GrokipediaProvider(base_url=base_url).fetch(topic)
    print(json.dumps({
        "provider": document.provider,
        "title": document.title,
        "url": document.url,
        "content_digest": document.content_digest,
        "references": len(document.references),
        "unofficial": document.unofficial,
    }, indent=2))
    return 0


def _constitutions_list() -> int:
    registry = default_registry()
    packages = registry.list()
    return _print_package_catalog(packages)


def _protocols_list() -> int:
    """Advertise protocol IDs and their exact schema identifiers to agents."""
    protocols = [
        {"protocol_id": protocol_id, "schema_id": load_schema(protocol_id)["$id"]}
        for protocol_id in protocol_ids()
    ]
    print(json.dumps({
        "schema": "aafp.commons/protocol-catalog@1",
        "protocols": protocols,
        "count": len(protocols),
    }, indent=2))
    return 0


def _protocols_show(protocol_id: str, raw: bool = False) -> int:
    try:
        schema = load_schema(protocol_id)
    except KeyError as error:
        print(json.dumps({"schema": "aafp.commons/protocol-error@1", "error": str(error)}))
        return 1
    if raw:
        print(json.dumps(schema, indent=2))
        return 0
    print(json.dumps({
        "schema": "aafp.commons/protocol-show@1",
        "protocol_id": protocol_id,
        "schema_document": schema,
    }, indent=2))
    return 0


def _sharing_export(root: Path, output: Path) -> int:
    snapshot = export_public_snapshot(CommonsRepository(root), output)
    print(json.dumps({"schema": snapshot["schema"], "exported": True,
                      "output": str(output), "count": snapshot["count"]}, indent=2))
    return 0


def _sharing_search(
    snapshot: Path, query: str, namespace: str | None, packet_kind: str | None, limit: int
) -> int:
    try:
        value = search_public_snapshot(
            load_public_snapshot(snapshot), query,
            namespace=namespace, packet_kind=packet_kind, limit=limit,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"schema": "aafp.commons/research-error@1", "error": str(error)}))
        return 1
    print(json.dumps({"schema": "aafp.commons/research-search@1", "query": query,
                      "results": value, "count": len(value)}, indent=2))
    return 0


def _sharing_verify(snapshot: Path) -> int:
    try:
        value = load_public_snapshot(snapshot)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"schema": "aafp.commons/research-error@1", "error": str(error)}))
        return 1
    print(json.dumps({"schema": "aafp.commons/research-snapshot@1", "verified": True,
                      "path": str(snapshot), "count": value["count"]}, indent=2))
    return 0


def _sharing_index(snapshots: list[Path], output: Path) -> int:
    index = PublicResearchIndex()
    try:
        added = sum(index.ingest(load_public_snapshot(path)) for path in snapshots)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"schema": "aafp.commons/research-error@1", "error": str(error)}))
        return 1
    index.save(output)
    print(json.dumps({"schema": "aafp.commons/research-index@1", "saved": True,
                      "output": str(output), "added": added, "count": len(index)}, indent=2))
    return 0


def _sharing_stats(index_path: Path) -> int:
    try:
        index = PublicResearchIndex.load(index_path)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"schema": "aafp.commons/research-error@1", "error": str(error)}))
        return 1
    print(json.dumps({"schema": "aafp.commons/research-stats@1", **index.stats()}, indent=2))
    return 0


def _print_package_catalog(packages: tuple[ConstitutionPackage, ...]) -> int:
    print(json.dumps({
        "schema": CATALOG_SCHEMA,
        "packages": [
            {
                "package_id": pkg.package_id,
                "version": pkg.version,
                "digest": pkg.manifest.manifest_digest,
                "display_name": pkg.display_name,
                "description": pkg.description,
                "tags": list(pkg.tags),
                "has_guidance": pkg.manifest.guidance is not None,
                "has_source": pkg.manifest.source is not None,
                "provider_constraint_policy": pkg.manifest.provider_constraint_policy,
                "namespace_prefixes": list(pkg.manifest.namespace_prefixes),
                "allowed_kinds": list(pkg.manifest.allowed_kinds),
                "compatible_runtimes": list(
                    pkg.manifest.runtime_compatibility.compatible
                    if pkg.manifest.runtime_compatibility is not None else ()
                ),
                "incompatible_runtimes": list(
                    pkg.manifest.runtime_compatibility.incompatible
                    if pkg.manifest.runtime_compatibility is not None else ()
                ),
                "source": pkg.manifest.source.to_dict()
                if pkg.manifest.source is not None else None,
            }
            for pkg in packages
        ],
        "count": len(packages),
    }, indent=2))
    return 0


def _constitutions_search(query: str) -> int:
    return _print_package_catalog(default_registry().search(query))


def _constitutions_show(package_id: str) -> int:
    registry = default_registry()
    try:
        parts = package_id.rsplit("@", 1)
        package = registry.get(parts[0], parts[1] if len(parts) == 2 else None)
    except ConstitutionPackageNotFoundError as error:
        print(json.dumps({
            "schema": "aafp.commons/constitution-package-error@1",
            "error": str(error),
        }))
        return 1
    manifest = package.manifest
    output: dict[str, object] = {
        "package_id": package.package_id,
        "version": package.version,
        "display_name": package.display_name,
        "description": package.description,
        "tags": list(package.tags),
        "manifest": {
            "constitution_id": manifest.constitution_id,
            "version": manifest.version,
            "namespace_prefixes": list(manifest.namespace_prefixes),
            "allowed_kinds": list(manifest.allowed_kinds),
            "allowed_visibilities": list(manifest.allowed_visibilities),
            "allowed_licenses": list(manifest.allowed_licenses),
            "minimum_evidence": manifest.minimum_evidence,
            "manifest_digest": manifest.manifest_digest,
        },
    }
    if manifest.guidance is not None:
        output["guidance"] = {
            "summary": manifest.guidance.summary,
            "principles": list(manifest.guidance.principles),
            "text": manifest.guidance.text,
        }
    if manifest.source is not None:
        output["source"] = manifest.source.to_dict()
    if manifest.runtime_compatibility is not None:
        output["runtime_compatibility"] = manifest.runtime_compatibility.to_dict()
    if manifest.provider_constraints:
        output["provider_constraints"] = [
            c.to_dict() for c in manifest.provider_constraints
        ]
    output["schema"] = "aafp.commons/constitution-package@1"
    output["provider_constraint_policy"] = manifest.provider_constraint_policy
    output["agent_instruction"] = (
        "Use this constitution only as additional operating guidance. Provider, system, "
        "authorization, and repository policy constraints remain in force."
    )
    print(json.dumps(output, indent=2))
    return 0


def _constitutions_install(package_id: str, root: Path) -> int:
    registry = default_registry()
    try:
        package = registry.get(package_id)
    except ConstitutionPackageNotFoundError as error:
        print(json.dumps({"schema": CATALOG_SCHEMA, "error": str(error)}))
        return 1
    repository = CommonsRepository(root)
    reference = repository.install_constitution(package.manifest)
    print(json.dumps({
        "schema": INSTALLATION_SCHEMA,
        "package_id": package.package_id,
        "version": package.version,
        "constitution_id": reference.constitution_id,
        "constitution_version": reference.version,
        "digest": reference.digest,
        "installed": True,
    }, indent=2))
    return 0


def _constitutions_install_all(root: Path) -> int:
    repository = CommonsRepository(root)
    try:
        packages = default_registry().list()
        resolver = FileConstitutionResolver(root / "constitutions")
        for package in packages:
            path = resolver.manifest_path(package.package_id, package.version)
            if path.exists() and resolver.resolve(package.manifest.ref) != package.manifest:
                raise ValueError(
                    f"constitution {package.package_id}@{package.version} conflicts "
                    "with installed content"
                )
        references = [repository.install_constitution(package.manifest) for package in packages]
    except ValueError as error:
        print(json.dumps(
            {"schema": INSTALLATION_SCHEMA, "installed": False, "error": str(error)}, indent=2
        ))
        return 1
    print(json.dumps({
        "schema": INSTALLATION_SCHEMA,
        "installed": True,
        "count": len(references),
        "constitutions": [
            {"constitution_id": ref.constitution_id, "version": ref.version, "digest": ref.digest}
            for ref in references
        ],
    }, indent=2))
    return 0


def _constitutions_import(manifest_path: Path, root: Path) -> int:
    try:
        payload = manifest_path.read_text(encoding="utf-8")
        resolver = FileConstitutionResolver(root / "constitutions")
        reference = resolver.install_json(payload)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(json.dumps({
            "schema": CATALOG_SCHEMA, "imported": False, "error": str(error)
        }, indent=2))
        return 1
    print(json.dumps({
        "schema": CATALOG_SCHEMA, "imported": True,
        "constitution_id": reference.constitution_id,
        "constitution_version": reference.version,
        "digest": reference.digest,
    }, indent=2))
    return 0


def _constitutions_export(reference: str, root: Path, output: Path) -> int:
    parts = reference.split("@")
    if len(parts) != 2 or not all(parts):
        print(json.dumps({"schema": CATALOG_SCHEMA, "exported": False,
                          "error": "reference must use ID@VERSION"}, indent=2))
        return 1
    try:
        resolver = FileConstitutionResolver(root / "constitutions")
        manifest = resolver.resolve(ConstitutionRef(parts[0], parts[1]))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(manifest.to_json(), encoding="utf-8")
    except (OSError, ValueError) as error:
        print(json.dumps({"schema": CATALOG_SCHEMA, "exported": False,
                          "error": str(error)}, indent=2))
        return 1
    print(json.dumps({"schema": CATALOG_SCHEMA, "exported": True,
                      "constitution_id": manifest.constitution_id,
                      "constitution_version": manifest.version,
                      "digest": manifest.manifest_digest,
                      "path": str(output)}, indent=2))
    return 0


def _constitutions_import_dir(directory: Path, root: Path) -> int:
    try:
        paths = sorted(directory.rglob("*.json"))
        if not paths:
            raise ValueError("manifest directory contains no JSON files")
        manifests = []
        for path in paths:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError(f"{path.name}: manifest must be a JSON object")
            manifests.append(ConstitutionManifest.from_dict(value))
        repository = CommonsRepository(root)
        seen: dict[tuple[str, str], ConstitutionManifest] = {}
        for manifest in manifests:
            key = (manifest.constitution_id, manifest.version)
            if key in seen and seen[key] != manifest:
                raise ValueError(
                    "bundle contains conflicting content for "
                    f"{manifest.constitution_id}@{manifest.version}"
                )
            seen[key] = manifest
            try:
                existing = repository.constitutions.resolve(
                    ConstitutionRef(manifest.constitution_id, manifest.version)
                )
            except ValueError:
                existing = None
            if existing is not None and existing != manifest:
                raise ValueError(
                    "existing constitution "
                    f"{manifest.constitution_id}@{manifest.version} has different content"
                )
        references = [repository.install_constitution(manifest) for manifest in seen.values()]
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"schema": CATALOG_SCHEMA, "imported": False,
                          "error": str(error)}, indent=2))
        return 1
    print(json.dumps({"schema": CATALOG_SCHEMA, "imported": True,
                      "count": len(references),
                      "constitutions": [
                          {"constitution_id": ref.constitution_id,
                           "version": ref.version, "digest": ref.digest}
                          for ref in references
                      ]}, indent=2))
    return 0


def _constitutions_verify(root: Path) -> int:
    resolver = FileConstitutionResolver(root / "constitutions")
    try:
        manifests = resolver.list()
    except ValueError as error:
        print(json.dumps({
            "schema": CATALOG_SCHEMA,
            "valid": False,
            "error": str(error),
        }, indent=2))
        return 1
    print(json.dumps({
        "schema": CATALOG_SCHEMA,
        "valid": True,
        "count": len(manifests),
        "constitutions": [
            {
                "constitution_id": manifest.constitution_id,
                "version": manifest.version,
                "digest": manifest.manifest_digest,
            }
            for manifest in manifests
        ],
    }, indent=2))
    return 0


def _catalog_list(root: Path) -> int:
    catalog = ConstitutionCatalog(FileConstitutionResolver(root / "constitutions"))
    summaries = catalog.list()
    if not summaries:
        print(json.dumps({
            "schema": CATALOG_SCHEMA,
            "constitutions": [],
            "count": 0,
        }, indent=2))
        return 0
    print(json.dumps({
        "schema": CATALOG_SCHEMA,
        "constitutions": [
            {
                "constitution_id": s.constitution_id,
                "version": s.version,
                "digest": s.digest,
                "description": s.description,
                "compatible_runtimes": list(s.compatible_runtimes),
                "incompatible_runtimes": list(s.incompatible_runtimes),
                "has_guidance": s.has_guidance,
                "source_license": s.source_license,
                "source_title": s.source_title,
                "provider_constraints": s.provider_count,
            }
            for s in summaries
        ],
        "count": len(summaries),
    }, indent=2))
    return 0


def _catalog_select(
    root: Path,
    runtime: str | None,
    namespace: str | None,
    packet_kind: str | None,
    require_guidance: bool,
) -> int:
    catalog = ConstitutionCatalog(FileConstitutionResolver(root / "constitutions"))
    manifest = catalog.select(
        runtime=runtime,
        namespace=namespace,
        packet_kind=packet_kind,
        require_guidance=require_guidance,
    )
    if manifest is None:
        print(json.dumps({
            "schema": SELECTION_SCHEMA,
            "selected": None,
            "reason": "no constitution matched",
        }, indent=2))
        return 1
    guidance = manifest.guidance
    print(json.dumps({
        "schema": SELECTION_SCHEMA,
        "selected": True,
        "constitution_ref": {
            "constitution_id": manifest.ref.constitution_id,
            "version": manifest.ref.version,
            "digest": manifest.ref.digest,
        },
        "namespace_prefixes": list(manifest.namespace_prefixes),
        "allowed_kinds": list(manifest.allowed_kinds),
        "guidance": None if guidance is None else {
            "summary": guidance.summary,
            "principles": list(guidance.principles),
            "text": guidance.text,
        },
        "provider_constraint_policy": manifest.provider_constraint_policy,
        "boundary": (
            "Selection records policy preference only. It does not prove AAFP identity, "
            "grant authority, establish provenance, or assign reputation."
        ),
    }, indent=2))
    return 0


def _agent_ask(
    root: Path,
    agent_id: str,
    runtime: str,
    namespace: str,
    packet_kind: str,
    purpose: str,
    constitution: str | None,
) -> int:
    repository = CommonsRepository(root)
    catalog = ConstitutionCatalog(FileConstitutionResolver(root / "constitutions"))
    try:
        result = catalog.request_adoption(
            requester_agent_id=agent_id,
            runtime=runtime,
            namespace=namespace,
            packet_kind=packet_kind,
            purpose=purpose,
            constitution=constitution,
        )
    except ValueError as error:
        print(json.dumps({
            "schema": "aafp.commons/constitution-adoption-request@1",
            "requested": False,
            "error": str(error),
        }, indent=2))
        return 1
    if result is None:
        print(json.dumps({
            "schema": "aafp.commons/constitution-adoption-request@1",
            "requested": False,
            "reason": "no compatible installed constitution with guidance matched",
        }, indent=2))
        return 1
    request, manifest = result
    try:
        repository.record_adoption_request(request)
    except ValueError as error:
        print(json.dumps({
            "schema": "aafp.commons/constitution-adoption-request@1",
            "requested": False,
            "error": str(error),
        }, indent=2))
        return 1
    guidance = manifest.guidance
    print(json.dumps({
        **request.to_dict(),
        "request_id": request.request_id,
        "requested": True,
        "question": request.question,
        "guidance": None if guidance is None else {
            "summary": guidance.summary,
            "principles": list(guidance.principles),
            "text": guidance.text,
        },
        "provider_constraints": [
            constraint.to_dict() for constraint in manifest.provider_constraints
        ],
        "boundary": ADOPTION_BOUNDARY,
        "acceptance_effect": (
            "The runtime may use the digest-pinned guidance as an additional preference. "
            "Acceptance grants no capability or repository permission."
        ),
    }, indent=2))
    return 0


def _agent_join(
    root: Path,
    agent_id: str,
    runtime: str,
    runtime_version: str,
    identity_convention: str,
    identity_hint: str,
    namespace: str,
    packet_kind: str,
    purpose: str,
    constitution: str | None,
    accepted_constitutions: list[str],
) -> int:
    """Start one composed handshake-to-adoption session."""
    try:
        resolver = FileConstitutionResolver(root / "constitutions")
        accepted_refs = []
        for value in accepted_constitutions:
            parts = value.split("@")
            if len(parts) != 2 or not all(parts):
                raise ValueError("accepted constitutions must use ID@VERSION")
            accepted_refs.append(resolver.resolve(ConstitutionRef(parts[0], parts[1])).ref)
        session = AgentJoinSession.begin(
            CommonsRepository(root),
            RuntimeHandshake(
                runtime=runtime,
                runtime_version=runtime_version,
                identity_convention=identity_convention,
                identity_hint=identity_hint,
                accepted_constitutions=tuple(accepted_refs),
            ),
            agent_id=agent_id,
            namespace=namespace,
            packet_kind=packet_kind,  # type: ignore[arg-type]
            purpose=purpose,
            constitution=constitution,
        )
    except ValueError as error:
        print(json.dumps({
            "schema": "aafp.commons/agent-join@1",
            "joined": False,
            "error": str(error),
        }, indent=2))
        return 1
    print(json.dumps({
        "schema": "aafp.commons/agent-join@1",
        "joined": True,
        "active": False,
        "requires_acceptance": True,
        "state": session.state,
        "handshake_id": session.handshake_id,
        "request_id": session.request.request_id,
        "question": session.request.question,
        "constitution": session.request.constitution.__dict__,
        "guidance": None if session.manifest.guidance is None else {
            "summary": session.manifest.guidance.summary,
            "principles": list(session.manifest.guidance.principles),
            "text": session.manifest.guidance.text,
        },
        "provider_constraints": [
            constraint.to_dict() for constraint in session.manifest.provider_constraints
        ],
        "provider_constraint_policy": session.manifest.provider_constraint_policy,
        "boundary": ADOPTION_BOUNDARY,
        "next_action": {
            "command": "agent respond",
            "required": True,
            "request_id": session.request.request_id,
            "handshake_id": session.handshake_id,
            "accept_command": (
                f"agent respond <root> {session.request.request_id} --accept"
            ),
            "context_command": (
                f"agent context <root> {session.request.request_id} "
                f"--handshake-id {session.handshake_id}"
            ),
            "description": "runtime must accept or reject before context is active",
        },
    }, indent=2))
    return 0


def _agent_requests(root: Path) -> int:
    repository = CommonsRepository(root)
    try:
        requests = repository.adoption_requests.list()
    except ValueError as error:
        print(json.dumps({
            "schema": "aafp.commons/constitution-adoption-request-list@1",
            "error": str(error),
        }, indent=2))
        return 1
    print(json.dumps({
        "schema": "aafp.commons/constitution-adoption-request-list@1",
        "requests": [
            {**request.to_dict(), "request_id": request.request_id}
            for request in requests
        ],
        "count": len(requests),
        "boundary": ADOPTION_BOUNDARY,
    }, indent=2))
    return 0


def _agent_respond(
    root: Path,
    request_id: str,
    accepted: bool,
    reason: str,
) -> int:
    repository = CommonsRepository(root)
    try:
        decision = repository.respond_to_adoption_request(
            request_id,
            accepted=accepted,
            reason=reason,
        )
    except ValueError as error:
        print(json.dumps({
            "schema": "aafp.commons/constitution-adoption-decision@1",
            "recorded": False,
            "error": str(error),
        }, indent=2))
        return 1
    print(json.dumps({
        **decision.to_dict(),
        "decision_id": decision.decision_id,
        "status": decision.status,
        "recorded": True,
        "boundary": ADOPTION_BOUNDARY,
        "effect": (
            "This local runtime decision controls guidance context only. It grants no "
            "identity, capability, repository permission, provenance, or reputation."
        ),
    }, indent=2))
    return 0


def _agent_context(root: Path, request_id: str, handshake_id: str | None = None) -> int:
    repository = CommonsRepository(root)
    try:
        request = repository.adoption_requests.get(request_id)
        decision = repository.adoption_decisions.get(request_id)
        manifest = repository.resolve_adopted_constitution(request_id)
        handshake = None
        if handshake_id is not None:
            handshake = repository.runtime_handshakes.get(handshake_id)
            if handshake.runtime != request.runtime:
                raise ValueError("handshake runtime does not match adoption request runtime")
    except ValueError as error:
        print(json.dumps({
            "schema": "aafp.commons/constitution-working-context@1",
            "active": False,
            "error": str(error),
        }, indent=2))
        return 1
    guidance = manifest.guidance
    print(json.dumps({
        "schema": "aafp.commons/constitution-working-context@1",
        "active": True,
        "request_id": request.request_id,
        "decision_id": decision.decision_id,
        **({"handshake_id": handshake.handshake_id} if handshake is not None else {}),
        "runtime": request.runtime,
        "namespace": request.namespace,
        "packet_kind": request.packet_kind,
        "constitution": request.constitution.__dict__,
        "guidance": None if guidance is None else {
            "summary": guidance.summary,
            "principles": list(guidance.principles),
            "text": guidance.text,
        },
        "provider_constraints": [
            constraint.to_dict() for constraint in manifest.provider_constraints
        ],
        "provider_constraint_policy": manifest.provider_constraint_policy,
        "boundary": ADOPTION_BOUNDARY,
    }, indent=2))
    return 0


def _runtime_handshake(
    root: Path,
    runtime: str,
    runtime_version: str,
    identity_convention: str,
    identity_hint: str,
    accepted_specs: list[str],
) -> int:
    repository = CommonsRepository(root)
    resolver = FileConstitutionResolver(root / "constitutions")
    references = []
    try:
        for spec in accepted_specs:
            if "@" not in spec:
                raise ValueError("accepted constitution must use <id>@<version>")
            constitution_id, version = spec.rsplit("@", 1)
            references.append(resolver.resolve(ConstitutionRef(constitution_id, version)).ref)
        handshake = RuntimeHandshake(
            runtime=runtime,
            runtime_version=runtime_version,
            identity_convention=identity_convention,
            identity_hint=identity_hint,
            accepted_constitutions=tuple(references),
        )
        repository.record_runtime_handshake(handshake)
    except ValueError as error:
        print(json.dumps({
            "schema": "aafp.commons/runtime-handshake@1",
            "recorded": False,
            "error": str(error),
        }, indent=2))
        return 1
    print(json.dumps({
        **handshake.to_dict(),
        "handshake_id": handshake.handshake_id,
        "recorded": True,
        "boundary": HANDSHAKE_BOUNDARY,
    }, indent=2))
    return 0


def _runtime_handshakes(root: Path) -> int:
    repository = CommonsRepository(root)
    try:
        handshakes = repository.runtime_handshakes.list()
    except ValueError as error:
        print(json.dumps({
            "schema": "aafp.commons/runtime-handshake-list@1",
            "error": str(error),
        }, indent=2))
        return 1
    print(json.dumps({
        "schema": "aafp.commons/runtime-handshake-list@1",
        "handshakes": [
            {**handshake.to_dict(), "handshake_id": handshake.handshake_id}
            for handshake in handshakes
        ],
        "count": len(handshakes),
        "boundary": HANDSHAKE_BOUNDARY,
    }, indent=2))
    return 0


def _runtime_handshake_show(root: Path, handshake_id: str) -> int:
    try:
        handshake = CommonsRepository(root).runtime_handshakes.get(handshake_id)
    except ValueError as error:
        print(json.dumps({
            "schema": "aafp.commons/runtime-handshake@1",
            "error": str(error),
        }, indent=2))
        return 1
    print(json.dumps({
        **handshake.to_dict(),
        "handshake_id": handshake.handshake_id,
        "boundary": HANDSHAKE_BOUNDARY,
    }, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aafp-commons")
    commands = parser.add_subparsers(dest="command", required=True)
    protocols = commands.add_parser("protocols", help="discover supported protocol schemas")
    protocol_commands = protocols.add_subparsers(dest="protocol_command", required=True)
    protocol_commands.add_parser(
        "list", help="list bundled protocol IDs and schema IDs"
    )
    protocol_show = protocol_commands.add_parser("show", help="show one bundled schema")
    protocol_show.add_argument("protocol_id")
    protocol_show.add_argument(
        "--raw", action="store_true", help="emit the schema document directly"
    )
    demo = commands.add_parser("demo", help="create and verify a local signed commons")
    demo.add_argument("root", type=Path)
    verify = commands.add_parser("verify", help="verify packets and the ledger")
    verify.add_argument("root", type=Path)
    grokipedia = commands.add_parser("grokipedia", help="query the unofficial Grokipedia adapter")
    grokipedia.add_argument("topic")
    grokipedia.add_argument("--base-url", default=DEFAULT_BASE_URL)
    constitutions = commands.add_parser(
        "constitutions", help="discover and install built-in constitution packages"
    )
    constitution_commands = constitutions.add_subparsers(
        dest="constitution_command", required=True
    )
    constitution_commands.add_parser("list", help="list available built-in packages")
    verify_constitutions = constitution_commands.add_parser(
        "verify", help="verify installed constitution manifests and content addresses"
    )
    verify_constitutions.add_argument("root", type=Path)
    search = constitution_commands.add_parser(
        "search", help="search available built-in packages by id, description, or tag"
    )
    search.add_argument("query")
    show = constitution_commands.add_parser("show", help="show details for one package")
    show.add_argument("package_id", help="package ID or exact ID@VERSION")
    install = constitution_commands.add_parser(
        "install", help="install a built-in package into a local repository"
    )
    install.add_argument("package_id")
    install.add_argument("root", type=Path)
    install_all = constitution_commands.add_parser(
        "install-all", help="install all built-in constitution packages"
    )
    install_all.add_argument("root", type=Path)
    imported = constitution_commands.add_parser(
        "import", help="import and validate a manifest JSON file"
    )
    imported.add_argument("manifest", type=Path)
    imported.add_argument("root", type=Path)
    exported = constitution_commands.add_parser(
        "export", help="export one exact installed manifest as portable JSON"
    )
    exported.add_argument("reference", help="constitution ID@VERSION")
    exported.add_argument("root", type=Path)
    exported.add_argument("output", type=Path)
    import_dir = constitution_commands.add_parser(
        "import-dir", help="validate and import every JSON manifest in a directory"
    )
    import_dir.add_argument("directory", type=Path)
    import_dir.add_argument("root", type=Path)
    catalog = commands.add_parser(
        "catalog", help="discover and select installed constitutions in a repository"
    )
    catalog_commands = catalog.add_subparsers(dest="catalog_command", required=True)
    catalog_list = catalog_commands.add_parser(
        "list", help="list installed constitutions with discovery metadata"
    )
    catalog_list.add_argument("root", type=Path)
    catalog_select = catalog_commands.add_parser(
        "select", help="select a constitution by runtime, namespace, or packet kind"
    )
    catalog_select.add_argument("root", type=Path)
    catalog_select.add_argument("--runtime", default=None)
    catalog_select.add_argument("--namespace", default=None)
    catalog_select.add_argument("--kind", default=None, dest="packet_kind")
    catalog_select.add_argument(
        "--require-guidance", action="store_true", help="only select constitutions with guidance"
    )
    agent = commands.add_parser(
        "agent", help="agent-originated optional constitution requests"
    )
    agent_commands = agent.add_subparsers(dest="agent_command", required=True)
    ask = agent_commands.add_parser(
        "ask", help="ask a runtime to adopt compatible optional guidance"
    )
    ask.add_argument("root", type=Path)
    ask.add_argument("--agent-id", required=True)
    ask.add_argument("--runtime", required=True)
    ask.add_argument("--namespace", required=True)
    ask.add_argument("--kind", required=True, dest="packet_kind")
    ask.add_argument("--purpose", default="")
    ask.add_argument(
        "--constitution", default=None, help="exact constitution ID@VERSION to request"
    )
    join = agent_commands.add_parser("join", help="start a handshake-to-adoption session")
    join.add_argument("root", type=Path)
    join.add_argument("--agent-id", required=True)
    join.add_argument("--runtime", required=True)
    join.add_argument("--runtime-version", required=True)
    join.add_argument("--identity-convention", required=True)
    join.add_argument("--identity-hint", required=True)
    join.add_argument("--namespace", required=True)
    join.add_argument("--kind", required=True, dest="packet_kind")
    join.add_argument("--purpose", default="")
    join.add_argument("--constitution", default=None)
    join.add_argument("--accepted-constitution", action="append", default=[])
    requests = agent_commands.add_parser(
        "requests", help="list durable agent-originated adoption requests"
    )
    requests.add_argument("root", type=Path)
    respond = agent_commands.add_parser(
        "respond", help="record a local runtime response to an agent request"
    )
    respond.add_argument("root", type=Path)
    respond.add_argument("request_id")
    outcome = respond.add_mutually_exclusive_group(required=True)
    outcome.add_argument("--accept", action="store_true")
    outcome.add_argument("--reject", action="store_true")
    respond.add_argument("--reason", default="")
    context = agent_commands.add_parser(
        "context", help="emit working guidance for an accepted request"
    )
    context.add_argument("root", type=Path)
    context.add_argument("request_id")
    context.add_argument(
        "--handshake-id",
        default=None,
        help="optional handshake ID emitted by agent join; validates runtime linkage",
    )
    runtime = commands.add_parser(
        "runtime", help="runtime self-description and handshake discovery"
    )
    runtime_commands = runtime.add_subparsers(dest="runtime_command", required=True)
    handshake = runtime_commands.add_parser("handshake", help="record a runtime handshake")
    handshake.add_argument("root", type=Path)
    handshake.add_argument("--runtime", required=True)
    handshake.add_argument("--runtime-version", required=True)
    handshake.add_argument("--identity-convention", required=True)
    handshake.add_argument("--identity-hint", required=True)
    handshake.add_argument("--accepted-constitution", action="append", default=[])
    handshakes = runtime_commands.add_parser("handshakes", help="list runtime handshakes")
    handshakes.add_argument("root", type=Path)
    handshake_show = runtime_commands.add_parser("handshake-show", help="show one handshake")
    handshake_show.add_argument("root", type=Path)
    handshake_show.add_argument("handshake_id")
    sharing = commands.add_parser("sharing", help="portable public research exchange")
    sharing_commands = sharing.add_subparsers(dest="sharing_command", required=True)
    sharing_export = sharing_commands.add_parser("export", help="export public packets")
    sharing_export.add_argument("root", type=Path)
    sharing_export.add_argument("output", type=Path)
    sharing_search = sharing_commands.add_parser("search", help="search a public snapshot")
    sharing_search.add_argument("snapshot", type=Path)
    sharing_search.add_argument("query")
    sharing_search.add_argument("--namespace")
    sharing_search.add_argument("--kind", dest="packet_kind")
    sharing_search.add_argument("--limit", type=int, default=100)
    sharing_verify = sharing_commands.add_parser("verify", help="verify a public snapshot")
    sharing_verify.add_argument("snapshot", type=Path)
    sharing_index = sharing_commands.add_parser("index", help="build a durable index")
    sharing_index.add_argument("output", type=Path)
    sharing_index.add_argument("snapshots", type=Path, nargs="+")
    sharing_stats = sharing_commands.add_parser("stats", help="show index health metrics")
    sharing_stats.add_argument("index", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "demo":
        return _demo(args.root)
    if args.command == "verify":
        return _verify(args.root)
    if args.command == "grokipedia":
        return _grokipedia(args.topic, args.base_url)
    if args.command == "constitutions":
        if args.constitution_command == "list":
            return _constitutions_list()
        if args.constitution_command == "search":
            return _constitutions_search(args.query)
        if args.constitution_command == "verify":
            return _constitutions_verify(args.root)
        if args.constitution_command == "show":
            return _constitutions_show(args.package_id)
        if args.constitution_command == "install":
            return _constitutions_install(args.package_id, args.root)
        if args.constitution_command == "install-all":
            return _constitutions_install_all(args.root)
        if args.constitution_command == "import":
            return _constitutions_import(args.manifest, args.root)
        if args.constitution_command == "export":
            return _constitutions_export(args.reference, args.root, args.output)
        if args.constitution_command == "import-dir":
            return _constitutions_import_dir(args.directory, args.root)
    if args.command == "protocols" and args.protocol_command == "list":
        return _protocols_list()
    if args.command == "protocols" and args.protocol_command == "show":
        return _protocols_show(args.protocol_id, args.raw)
    if args.command == "catalog":
        if args.catalog_command == "list":
            return _catalog_list(args.root)
        if args.catalog_command == "select":
            return _catalog_select(
                args.root,
                args.runtime,
                args.namespace,
                args.packet_kind,
                args.require_guidance,
            )
    if args.command == "agent" and args.agent_command == "ask":
        return _agent_ask(
            args.root,
            args.agent_id,
            args.runtime,
            args.namespace,
            args.packet_kind,
            args.purpose,
            args.constitution,
        )
    if args.command == "agent" and args.agent_command == "join":
        return _agent_join(
            args.root, args.agent_id, args.runtime, args.runtime_version,
            args.identity_convention, args.identity_hint, args.namespace,
            args.packet_kind, args.purpose, args.constitution,
            args.accepted_constitution,
        )
    if args.command == "agent" and args.agent_command == "requests":
        return _agent_requests(args.root)
    if args.command == "agent" and args.agent_command == "respond":
        return _agent_respond(args.root, args.request_id, args.accept, args.reason)
    if args.command == "agent" and args.agent_command == "context":
        return _agent_context(args.root, args.request_id, args.handshake_id)
    if args.command == "runtime":
        if args.runtime_command == "handshake":
            return _runtime_handshake(
                args.root,
                args.runtime,
                args.runtime_version,
                args.identity_convention,
                args.identity_hint,
                args.accepted_constitution,
            )
        if args.runtime_command == "handshakes":
            return _runtime_handshakes(args.root)
        if args.runtime_command == "handshake-show":
            return _runtime_handshake_show(args.root, args.handshake_id)
    if args.command == "sharing" and args.sharing_command == "export":
        return _sharing_export(args.root, args.output)
    if args.command == "sharing" and args.sharing_command == "search":
        return _sharing_search(
            args.snapshot, args.query, args.namespace, args.packet_kind, args.limit
        )
    if args.command == "sharing" and args.sharing_command == "verify":
        return _sharing_verify(args.snapshot)
    if args.command == "sharing" and args.sharing_command == "index":
        return _sharing_index(args.snapshots, args.output)
    if args.command == "sharing" and args.sharing_command == "stats":
        return _sharing_stats(args.index)
    raise AssertionError(f"unhandled command {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
