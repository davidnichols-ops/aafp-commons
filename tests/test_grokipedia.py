from __future__ import annotations

import json
from types import TracebackType
from typing import Any

from aafp_commons.providers.grokipedia import GrokipediaProvider


class FakeResponse:
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps({
            "title": "Post-quantum cryptography",
            "url": "https://grokipedia.com/page/Post-quantum_cryptography",
            "content_text": "Cryptographic systems designed to resist quantum attacks.",
            "references": [{"number": 1, "url": "https://csrc.nist.gov/pqc"}],
        }).encode()


def test_grokipedia_adapter_preserves_provenance() -> None:
    calls: list[Any] = []

    def opener(request: Any, timeout: float) -> FakeResponse:
        calls.append((request.full_url, timeout))
        return FakeResponse()

    document = GrokipediaProvider(base_url="https://example.test", opener=opener).fetch(
        "Post-quantum cryptography"
    )
    assert calls[0][0].startswith("https://example.test/page/Post-quantum_cryptography")
    assert document.unofficial
    assert document.provider == "grokipedia-unofficial"
    assert document.references == ("https://csrc.nist.gov/pqc",)
    assert document.content_digest.startswith("sha256:")

