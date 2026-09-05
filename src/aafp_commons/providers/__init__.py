"""Research-provider adapters."""

from aafp_commons.providers.base import ResearchDocument, ResearchProvider
from aafp_commons.providers.grokipedia import GrokipediaProvider

__all__ = ["GrokipediaProvider", "ResearchDocument", "ResearchProvider"]

