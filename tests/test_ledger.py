from __future__ import annotations

import json
from pathlib import Path

from ironclad.trust import Identity

from aafp_commons.ledger import Ledger, merkle_root


def test_signed_ledger_chain_verifies(tmp_path: Path, identity: Identity) -> None:
    ledger = Ledger(tmp_path / "ledger.jsonl")
    first = ledger.append(("sha256:" + "1" * 64,), identity)
    second = ledger.append(("sha256:" + "2" * 64, "sha256:" + "3" * 64), identity)
    result = ledger.verify()
    assert result.valid
    assert result.blocks == 2
    assert result.packets == 3
    assert second.block.previous_hash == first.block.block_hash


def test_merkle_root_is_order_sensitive() -> None:
    assert merkle_root(("a", "b")) != merkle_root(("b", "a"))


def test_ledger_tampering_is_detected(tmp_path: Path, identity: Identity) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger(path)
    ledger.append(("sha256:" + "1" * 64,), identity)
    data = json.loads(path.read_text())
    data["block"]["packet_digests"] = ["sha256:" + "9" * 64]
    path.write_text(json.dumps(data) + "\n")
    assert not ledger.verify().valid

