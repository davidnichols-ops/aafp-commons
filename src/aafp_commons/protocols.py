"""Access to the bundled, versioned AAFP Commons protocol schemas."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

_PROTOCOLS = MappingProxyType({
    "agent-join@1": "agent-join@1.schema.json",
    "constitution-manifest@1": "constitution-manifest@1.schema.json",
    "constitution-package@1": "constitution-package@1.schema.json",
    "constitution-package-error@1": "constitution-package-error@1.schema.json",
    "constitution-adoption-request@1": "constitution-adoption-request@1.schema.json",
    "constitution-adoption-decision@1": "constitution-adoption-decision@1.schema.json",
    "constitution-adoption-envelope@1": "constitution-adoption-envelope@1.schema.json",
    "constitution-working-context@1": "constitution-working-context@1.schema.json",
    "constitution-catalog@1": "constitution-catalog@1.schema.json",
    "constitution-installation@1": "constitution-installation@1.schema.json",
    "constitution-selection@1": "constitution-selection@1.schema.json",
    "runtime-handshake@1": "runtime-handshake@1.schema.json",
    "runtime-handshake-envelope@1": "runtime-handshake-envelope@1.schema.json",
    "protocol-catalog@1": "protocol-catalog@1.schema.json",
    "protocol-error@1": "protocol-error@1.schema.json",
    "protocol-show@1": "protocol-show@1.schema.json",
    "constitution-adoption-request-list@1": "constitution-adoption-request-list@1.schema.json",
    "runtime-handshake-list@1": "runtime-handshake-list@1.schema.json",
    "research-snapshot@1": "research-snapshot@1.schema.json",
    "research-search@1": "research-search@1.schema.json",
    "research-index@1": "research-index@1.schema.json",
    "research-error@1": "research-error@1.schema.json",
    "research-stats@1": "research-stats@1.schema.json",
    "research-checkpoint@1": "research-checkpoint@1.schema.json",
    "research-publication@1": "research-publication@1.schema.json",
    "publication-state@1": "publication-state@1.schema.json",
    "research-delta@1": "research-delta@1.schema.json",
})


class ProtocolNotFoundError(KeyError):
    """Raised when a protocol identifier is not bundled."""


def protocol_ids() -> tuple[str, ...]:
    """Return the stable identifiers available in this package."""
    return tuple(_PROTOCOLS)


def schema_path(protocol_id: str) -> Any:
    """Return a traversable resource for a protocol schema."""
    try:
        filename = _PROTOCOLS[protocol_id]
    except KeyError as error:
        raise ProtocolNotFoundError(protocol_id) from error
    bundled = files("aafp_commons").joinpath("protocols", filename)
    if bundled.is_file():
        return bundled
    # In a source checkout, schemas live at the repository root; wheels place
    # them beside the package through hatch's force-include configuration.
    return Path(__file__).resolve().parents[2] / "protocols" / filename


def load_schema(protocol_id: str) -> dict[str, Any]:
    """Load one bundled schema as a JSON object."""
    return cast(dict[str, Any], json.loads(schema_path(protocol_id).read_text(encoding="utf-8")))
