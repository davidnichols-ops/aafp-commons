from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).parents[1] / "protocols"


def test_protocol_schema_index_files_are_valid_and_versioned() -> None:
    expected = {
        "agent-join@1.schema.json": "aafp.commons/agent-join@1",
        "constitution-manifest@1.schema.json": "aafp.commons/constitution-manifest@1",
        "constitution-package@1.schema.json": "aafp.commons/constitution-package@1",
        "constitution-package-error@1.schema.json": "aafp.commons/constitution-package-error@1",
        "constitution-catalog@1.schema.json": "aafp.commons/constitution-catalog@1",
        "constitution-selection@1.schema.json": "aafp.commons/constitution-selection@1",
        "constitution-installation@1.schema.json": "aafp.commons/constitution-installation@1",
        "constitution-adoption-request@1.schema.json":
            "aafp.commons/constitution-adoption-request@1",
        "constitution-adoption-decision@1.schema.json":
            "aafp.commons/constitution-adoption-decision@1",
        "constitution-adoption-envelope@1.schema.json":
            "aafp.commons/constitution-adoption-envelope@1",
        "constitution-working-context@1.schema.json":
            "aafp.commons/constitution-working-context@1",
        "runtime-handshake@1.schema.json": "aafp.commons/runtime-handshake@1",
        "protocol-catalog@1.schema.json": "aafp.commons/protocol-catalog@1",
        "protocol-error@1.schema.json": "aafp.commons/protocol-error@1",
        "protocol-show@1.schema.json": "aafp.commons/protocol-show@1",
        "constitution-adoption-request-list@1.schema.json":
            "aafp.commons/constitution-adoption-request-list@1",
        "runtime-handshake-list@1.schema.json":
            "aafp.commons/runtime-handshake-list@1",
        "research-snapshot@1.schema.json": "aafp.commons/research-snapshot@1",
        "research-search@1.schema.json": "aafp.commons/research-search@1",
        "research-index@1.schema.json": "aafp.commons/research-index@1",
        "research-error@1.schema.json": "aafp.commons/research-error@1",
        "research-stats@1.schema.json": "aafp.commons/research-stats@1",
        "research-checkpoint@1.schema.json": "aafp.commons/research-checkpoint@1",
        "research-publication@1.schema.json": "aafp.commons/research-publication@1",
        "publication-state@1.schema.json": "aafp.commons/publication-state@1",
        "research-delta@1.schema.json": "aafp.commons/research-delta@1",
        "runtime-handshake-envelope@1.schema.json":
            "aafp.commons/runtime-handshake-envelope@1",
    }
    for filename, schema_id in expected.items():
        document = json.loads((SCHEMA_DIR / filename).read_text(encoding="utf-8"))
        assert document["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert document["$id"].endswith(schema_id.rsplit("/", 1)[-1])
        assert document["type"] == "object"
        assert document["additionalProperties"] is False
        assert document["required"]
        assert document["properties"]["schema"]["const"] == schema_id


def test_shipped_manifests_validate_against_portable_schema() -> None:
    schema = json.loads(
        (SCHEMA_DIR / "constitution-manifest@1.schema.json").read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)
    for path in (SCHEMA_DIR.parent / "constitutions").glob("*/1.0.0.json"):
        validator.validate(json.loads(path.read_text(encoding="utf-8")))
