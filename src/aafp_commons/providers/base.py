"""Replaceable research-provider contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ResearchDocument:
    provider: str
    title: str
    url: str
    content: str
    retrieved_at: int
    content_digest: str
    references: tuple[str, ...] = ()
    unofficial: bool = False


class ResearchProvider(Protocol):
    def fetch(self, topic: str) -> ResearchDocument: ...

