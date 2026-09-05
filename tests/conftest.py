from __future__ import annotations

import time

import pytest
from ironclad.trust import Identity

from aafp_commons.constitutions import ConstitutionManifest
from aafp_commons.identity import derive_agent_id
from aafp_commons.models import EvidenceRef, KnowledgePacket, MethodRef


@pytest.fixture
def identity() -> Identity:
    return Identity.generate()


@pytest.fixture
def constitution() -> ConstitutionManifest:
    return ConstitutionManifest(
        constitution_id="frontier-dev",
        version="0.1",
        namespace_prefixes=("commons/frontend",),
        allowed_visibilities=("public", "organization"),
    )


@pytest.fixture
def packet(identity: Identity, constitution: ConstitutionManifest) -> KnowledgePacket:
    del identity  # AAFP authorship is intentionally not the Ironclad signer.
    return KnowledgePacket(
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
