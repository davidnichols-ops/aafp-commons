#!/usr/bin/env bash
# R3: Offline wheel-install regression test.
#
# Proves that uv pip install dist/*.whl followed by import, Ironclad signing,
# and `commons world` works without network access and without contacting
# /Users/david/Projects during the test phase.
#
# Usage:  bash tests/test_wheel_offline.sh
# Exit:   0 = pass, 1 = fail
#
# See contracts/R3-wheel-offline.md for the full contract.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_VENV_SITE="$(ls -d "$REPO_ROOT/.venv/lib/python"*/site-packages 2>/dev/null | head -1)"

STAGE="/tmp/commons-pass5-offline"
WHEELS="$STAGE/wheels"
DEPS="$STAGE/deps"
VENV="$STAGE/venv"
HOME_DIR="$STAGE/home"

AAFP_WHEEL="$REPO_ROOT/dist/aafp_commons-0.1.0-py3-none-any.whl"

fail() { echo "FAIL: $*" >&2; exit 1; }
ok()   { echo "ok: $*"; }

# ---------------------------------------------------------------------------
# Pre-flight: wheels and project venv must exist.
# ---------------------------------------------------------------------------
[[ -f "$AAFP_WHEEL" ]]          || fail "aafp-commons wheel not found at $AAFP_WHEEL"
[[ -d "$PROJECT_VENV_SITE" ]]   || fail "project venv site-packages not found at $PROJECT_VENV_SITE"

# ---------------------------------------------------------------------------
# Setup phase: stage wheels + transitive deps into /tmp.  This is the ONLY
# step that reads from /Users/david/Projects.  Everything after this runs
# from /tmp with no /Users/david/Projects access.
#
# The uv cache stores unpacked archives (archive-v0/), not .whl files, so
# uv pip install --offline cannot resolve transitive deps for a fresh venv.
# We therefore stage the already-installed transitive deps from the project
# venv (the "already-cached dependencies" per the contract) into /tmp during
# setup, then install them into the test venv from /tmp only.
# ---------------------------------------------------------------------------
rm -rf "$STAGE"
mkdir -p "$WHEELS" "$DEPS"
cp "$AAFP_WHEEL" "$WHEELS/"
ok "staged wheels into $WHEELS"

# Stage transitive deps: copy the installed packages + dist-info from the
# project venv.  These are the deps that ironclad requires (cbor2,
# cryptography, cffi, pycparser, pydantic, pydantic_core, pyyaml, tomli,
# liboqs) plus pydantic's deps (annotated_types, typing_extensions,
# typing_inspection).
DEP_NAMES="cbor2 cryptography cffi pycparser pydantic pydantic_core \
           yaml tomli liboqs annotated_types typing_extensions typing_inspection"
for name in $DEP_NAMES; do
    for item in "$PROJECT_VENV_SITE"/${name}* "$PROJECT_VENV_SITE"/${name//-/_}*; do
        [[ -e "$item" ]] && cp -r "$item" "$DEPS/"
    done
done
# Also copy _cffi_backend native extension (named with leading underscore).
for item in "$PROJECT_VENV_SITE"/_cffi_backend*; do
    [[ -e "$item" ]] && cp -r "$item" "$DEPS/"
done
# Copy dist-info dirs for all deps (handles underscore/hyphen variants).
for dist_info in "$PROJECT_VENV_SITE"/*.dist-info; do
    name_lower="$(basename "$dist_info" | tr '[:upper:]' '[:lower:]')"
    for dep in cbor2 cryptography cffi pycparser pydantic pyyaml tomli liboqs \
               annotated_types typing_extensions typing_inspection; do
        if [[ "$name_lower" == "${dep}"* ]]; then
            cp -r "$dist_info" "$DEPS/"
            break
        fi
    done
done
ok "staged transitive deps into $DEPS"

# ---------------------------------------------------------------------------
# Test phase: from here on, cwd=/tmp, PYTHONPATH empty, UV_OFFLINE=1.
# No reads from /Users/david/Projects.
# ---------------------------------------------------------------------------
cd /tmp
export PYTHONPATH=
export UV_OFFLINE=1
export COMMONS_HOME="$HOME_DIR"

# Create an isolated venv.
python3 -m venv "$VENV"
ok "created venv at $VENV"

VENV_SITE="$(ls -d "$VENV/lib/python"*/site-packages | head -1)"

# Install transitive deps from the staged /tmp copy (not from the project venv).
cp -r "$DEPS"/* "$VENV_SITE/"
ok "installed transitive deps from staged copy"

# Install the aafp-commons wheel with uv pip install --offline --no-deps.
# The wheel includes the vendored ironclad compatibility package. --no-deps
# is used because transitive deps are already in place.
# --offline blocks all network.  --find-links points at the /tmp wheels dir.
# This is the "uv pip install dist/*.whl" step the contract verifies.
uv pip install --offline --no-deps --find-links "$WHEELS" \
    "$WHEELS/aafp_commons-0.1.0-py3-none-any.whl" \
    --python "$VENV/bin/python"
ok "offline uv pip install of aafp-commons wheel with vendored ironclad"

# ---------------------------------------------------------------------------
# Functional check 1: import + module-location proof (no /Users/david/Projects).
# ---------------------------------------------------------------------------
"$VENV/bin/python" - <<'PYEOF'
import os, sys, pathlib

# --- Import from the installed wheel, not the source tree. ---
import aafp_commons
import ironclad

aafp_file = pathlib.Path(aafp_commons.__file__).resolve()
iron_file = pathlib.Path(ironclad.__file__).resolve()

# macOS symlinks /tmp → /private/tmp; resolve both sides for comparison.
VENVPREFIX = pathlib.Path("/tmp/commons-pass5-offline/venv").resolve()
FORBIDDEN  = "/Users/david/Projects"

assert str(aafp_file).startswith(str(VENVPREFIX)), (
    f"aafp_commons.__file__ not in venv: {aafp_file} (expected under {VENVPREFIX})"
)
assert str(iron_file).startswith(str(VENVPREFIX)), (
    f"ironclad.__file__ not in venv: {iron_file} (expected under {VENVPREFIX})"
)

# --- No sys.path entry may reference the source tree. ---
offenders = [p for p in sys.path if FORBIDDEN in p]
assert not offenders, f"/Users/david/Projects on sys.path: {offenders}"

print(f"ok: aafp_commons resolved at {aafp_file}")
print(f"ok: ironclad resolved at {iron_file}")
print(f"ok: sys.path clean (no {FORBIDDEN})")
PYEOF
ok "import + module-location proof"

# ---------------------------------------------------------------------------
# Functional check 2: Ironclad sign → verify → tamper → fail-closed.
# ---------------------------------------------------------------------------
"$VENV/bin/python" - <<'PYEOF'
import time
from ironclad.trust import Identity

from aafp_commons.identity import derive_agent_id
from aafp_commons.models import EvidenceRef, KnowledgePacket, MethodRef
from aafp_commons.constitutions import ConstitutionManifest
from aafp_commons.signing import sign_packet, SignedPacket

identity = Identity.generate()

constitution = ConstitutionManifest(
    constitution_id="frontier-dev",
    version="0.1",
    namespace_prefixes=("commons/frontend",),
    allowed_visibilities=("public", "organization"),
)

packet = KnowledgePacket(
    kind="finding",
    namespace="commons/frontend/react",
    claim="Comparing server and client inputs first reduces hydration debugging time.",
    scope={"framework": "react", "problem": "hydration"},
    evidence=(
        EvidenceRef(
            kind="reproduction",
            uri="artifact://tests/hydration-1",
            observed_at=int(time.time()),
        ),
    ),
    confidence=0.82,
    author_agent_id=derive_agent_id(b"fixture-aafp-agent-public-key"),
    constitution=constitution.ref,
    method=MethodRef("hydration-triage", "1.0"),
)

# Sign + verify round-trip.
signed = sign_packet(packet, identity)
assert signed.signer_key_id == identity.key_id, "signer_key_id mismatch"
assert signed.verify(), "signed packet failed verification"

# Tamper the packet claim → must fail closed.
tampered_data = signed.to_dict()
tampered_data["packet"]["claim"] = "This packet was tampered with after signing."
tampered = SignedPacket.from_dict(tampered_data)
assert not tampered.verify(), "tampered packet unexpectedly verified"

# Tamper the receipt namespace → must fail closed.
from copy import deepcopy
receipt_tampered = deepcopy(sign_packet(packet, identity).to_dict())
receipt_tampered["receipt"]["evidence"]["data"]["namespace"] = "commons/poisoned"
assert not SignedPacket.from_dict(receipt_tampered).verify(), \
    "tampered receipt unexpectedly verified"

print("ok: sign → verify → tamper → fail-closed round-trip")
PYEOF
ok "Ironclad signing round-trip"

# ---------------------------------------------------------------------------
# Functional check 3: commons world with COMMONS_HOME in /tmp.
# ---------------------------------------------------------------------------
COMMONS_HOME="$HOME_DIR" "$VENV/bin/commons" world > "$STAGE/world.json"
# world should produce valid JSON with expected keys.
"$VENV/bin/python" - "$STAGE/world.json" <<'PYEOF'
import json, sys
data = json.loads(open(sys.argv[1]).read())
assert "posture" in data, "missing 'posture' in world output"
assert "packet_count" in data, "missing 'packet_count' in world output"
assert data["posture"] == "source", f"unexpected posture: {data['posture']}"
print(f"ok: commons world posture={data['posture']} packets={data['packet_count']}")
PYEOF
ok "commons world from isolated home"

echo ""
echo "=== R3 offline wheel-install regression: PASS ==="
echo "  stage:       $STAGE"
echo "  venv:        $VENV"
echo "  home:        $HOME_DIR"
echo "  wheels:      $WHEELS"
echo "  deps:        $DEPS (staged from project venv during setup)"
echo "  offline:     UV_OFFLINE=1, --no-deps, --find-links"
echo "  no /Users/david/Projects contact during test phase"
