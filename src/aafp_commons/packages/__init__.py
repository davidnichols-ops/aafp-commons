"""Built-in constitution packages and agent-first discovery registry.

Three packages are shipped:

- ``anthropic-cc0`` — Anthropic's constitution distilled under CC0.
- ``grok-truth-seeking`` — user-provided truth-seeking and humanity guidance.
- ``gpt-astra-6`` — user-provided useful, honest, agency-preserving guidance.

Each package wraps an immutable :class:`ConstitutionManifest` with display
metadata for agent discovery. Installing a package produces the same
immutable manifest as constructing one directly — the package layer carries
no authority.
"""

from __future__ import annotations

from aafp_commons.packages.anthropic_cc0 import ANTHROPIC_CC0_PACKAGE
from aafp_commons.packages.base import (
    ConstitutionPackage,
    ConstitutionPackageError,
    ConstitutionPackageNotFoundError,
    ConstitutionPackageRegistry,
    ConstitutionPackageSource,
)
from aafp_commons.packages.gpt_astra_6 import GPT_ASTRA_6_PACKAGE
from aafp_commons.packages.grok_truth_seeking import GROK_TRUTH_SEEKING_PACKAGE

__all__ = [
    "ANTHROPIC_CC0_PACKAGE",
    "ConstitutionPackage",
    "ConstitutionPackageError",
    "ConstitutionPackageNotFoundError",
    "ConstitutionPackageRegistry",
    "ConstitutionPackageSource",
    "GPT_ASTRA_6_PACKAGE",
    "GROK_TRUTH_SEEKING_PACKAGE",
    "default_registry",
]


def default_registry() -> ConstitutionPackageRegistry:
    """Return a registry pre-loaded with all built-in constitution packages."""
    registry = ConstitutionPackageRegistry()
    registry.register(ANTHROPIC_CC0_PACKAGE)
    registry.register(GROK_TRUTH_SEEKING_PACKAGE)
    registry.register(GPT_ASTRA_6_PACKAGE)
    return registry
