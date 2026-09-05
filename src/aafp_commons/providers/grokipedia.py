"""Unofficial Grokipedia research adapter.

The upstream surface is not official and may change. The base URL and opener
are injectable so callers can self-host a compatible wrapper or replace it.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from aafp_commons.canonical import digest
from aafp_commons.providers.base import ResearchDocument

DEFAULT_BASE_URL = "https://spaceless.com/grokipedia"


class GrokipediaError(RuntimeError):
    pass


class GrokipediaProvider:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 15.0,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._opener = opener

    def fetch(self, topic: str) -> ResearchDocument:
        slug = urllib.parse.quote(topic.strip().replace(" ", "_"), safe=",_()-&")
        if not slug:
            raise ValueError("topic cannot be empty")
        endpoint = f"{self.base_url}/page/{slug}?extract_refs=true"
        request = urllib.request.Request(
            endpoint,
            headers={"Accept": "application/json", "User-Agent": "aafp-commons/0.1"},
        )
        try:
            with self._opener(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise GrokipediaError(f"unofficial Grokipedia request failed: {error}") from error
        content = payload.get("content_text")
        if not isinstance(content, str) or not content.strip():
            raise GrokipediaError("unofficial Grokipedia response did not contain article text")
        references = tuple(
            item["url"]
            for item in payload.get("references", [])
            if isinstance(item, dict) and isinstance(item.get("url"), str)
        )
        url = str(payload.get("url") or f"https://grokipedia.com/page/{slug}")
        return ResearchDocument(
            provider="grokipedia-unofficial",
            title=str(payload.get("title") or topic),
            url=url,
            content=content,
            retrieved_at=int(time.time()),
            content_digest=digest({"url": url, "content": content}),
            references=references,
            unofficial=True,
        )
