"""Vendored ironclad signing surface for aafp-commons.

This is a minimal, byte-for-byte compatible reimplementation of the
``ironclad.canon`` and ``ironclad.trust`` modules consumed by
``aafp_commons``. It preserves the ``ironclad-ed25519-v1`` packet format
without depending on the external ``ironclad`` package.

Only four symbols are exported across two modules:

- ``ironclad.canon.content_digest``
- ``ironclad.trust.Identity``
- ``ironclad.trust.Evidence``
- ``ironclad.trust.Receipt``
"""
