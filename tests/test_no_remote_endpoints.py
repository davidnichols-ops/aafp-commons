"""Guardrail: no remote endpoints or root SSH logins in tracked content.

This test fails if forbidden remote-endpoint patterns or the remote root login
prefix appear in git-tracked repository content. It is deterministic and
fully offline; the only subprocess is ``git ls-files``.

Self-safety: the test source file itself is tracked content. To avoid the
test's own scan matching its own forbidden strings, every sensitive fragment
is constructed at runtime from character codes or string fragments.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --- Forbidden fragments, constructed at runtime ---------------------------
#
# The remote root login prefix is assembled so its literal never appears here.
_ROOT_AT = "roo" + "t" + chr(64)
# The known endpoint fragments are assembled so the literals never appear here.
_HOST_FRAGMENTS = ("27" + ".64.", "84" + ".18.", "1" + ".208.")
# SSH port flag ``-p`` followed by a 5-digit port, then a user@host target.
# The regex is built from fragments so neither ``root`` nor ``@`` appear literally.
_SSH_PORT_RE = re.compile(
    chr(45) + chr(112) + r"\s+\d{4,5}\s+\S+" + chr(64) + r"[\d.]+"
)
def _tracked_files() -> list[Path]:
    """Return git-tracked files as absolute paths (deterministic, offline)."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line.strip()]


def _read_text(path: Path) -> str | None:
    """Read a file as text, skipping binaries (null bytes / decode errors)."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="replace")


def _scan(path: Path, content: str) -> list[str]:
    """Return a list of violation descriptions for *path*."""
    violations: list[str] = []
    if _ROOT_AT in content:
        violations.append(f"{_ROOT_AT!r} (remote root SSH login prefix)")
    for fragment in _HOST_FRAGMENTS:
        if fragment in content:
            violations.append("known remote endpoint fragment")
            break
    if _SSH_PORT_RE.search(content):
        violations.append("SSH -p <port> user@host endpoint pattern")
    return violations


def test_no_remote_endpoints_in_tracked_content() -> None:
    """No tracked file may contain remote endpoints or root SSH logins."""
    offenders: dict[str, list[str]] = {}
    for path in _tracked_files():
        content = _read_text(path)
        if content is None:
            continue
        found = _scan(path, content)
        if found:
            try:
                rel = path.relative_to(ROOT)
            except ValueError:
                rel = path
            offenders[str(rel)] = found
    assert not offenders, (
        "Forbidden remote-endpoint patterns found in tracked content:\n"
        + "\n".join(
            f"  {file}: {', '.join(violations)}"
            for file, violations in sorted(offenders.items())
        )
    )
