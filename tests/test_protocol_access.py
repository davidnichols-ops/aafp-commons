import pytest

from aafp_commons.protocols import ProtocolNotFoundError, load_schema, protocol_ids, schema_path


def test_bundled_protocol_access_loads_schema() -> None:
    assert len(protocol_ids()) == 27
    assert "agent-join@1" in protocol_ids()
    assert schema_path("agent-join@1").read_text(encoding="utf-8").startswith("{")
    assert load_schema("agent-join@1")["$id"].endswith("agent-join@1")


def test_unknown_protocol_is_explicit() -> None:
    with pytest.raises(ProtocolNotFoundError):
        schema_path("unknown@1")


def test_every_advertised_protocol_has_matching_schema() -> None:
    for protocol_id in protocol_ids():
        document = load_schema(protocol_id)
        assert document["$id"].endswith(protocol_id)
        assert document["properties"]["schema"]["const"] == f"aafp.commons/{protocol_id}"
