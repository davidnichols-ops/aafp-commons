import json
from pathlib import Path

import pytest

from aafp_commons.w1 import _follow, _read_peers, _unfollow


def test_follow_unfollow_accepts_loopback_only(tmp_path: Path):
    assert _follow(tmp_path, "http://127.0.0.1:8081")["peers"] == ["http://127.0.0.1:8081"]
    assert _read_peers(tmp_path) == ["http://127.0.0.1:8081"]
    assert _unfollow(tmp_path, "http://127.0.0.1:8081")["peers"] == []
    with pytest.raises(ValueError):
        _follow(tmp_path, "https://example.invalid/node")


def test_public_snapshot_is_a_local_file_import():
    snapshot = json.loads(Path("published/maos-lessons-public-2026-09-05.json").read_text())
    assert snapshot["schema"] == "aafp.commons/research-snapshot@1"
