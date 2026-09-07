from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_agent_facing_docs_contract() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    example = json.loads((ROOT / "commons.json.example").read_text(encoding="utf-8"))
    two_terminals = (ROOT / "examples" / "two-terminals.md").read_text(encoding="utf-8")
    workload = (ROOT / "docs" / "REAL-WORKLOAD.md").read_text(encoding="utf-8")

    assert len(readme.splitlines()) <= 80
    for required in (
        "If `commons` or `python -m aafp_commons` is available, start MCP",
        "Read posture from `commons_world` before writing.",
        "Do not assume a constitution unless the user said `join` or `commons.json`",
        "Proposals need evidence.",
        "Source posture is read-only.",
    ):
        assert required in agents
    assert example["join"] is False
    assert "contradiction" in two_terminals.lower()
    assert "resolution is not in this tree yet" in two_terminals.lower()
    for required in (
        "commons world",
        "commons policy show",
        "commons status CLAIM_ID",
        "Roboflow PR",
        "Lesson snapshot",
        "Training config",
        "rely_reason",
    ):
        assert required.lower() in workload.lower()
    for forbidden in ("consensus", "agi memory", "10k nodes", "brew", "npm"):
        assert forbidden not in readme.lower()
