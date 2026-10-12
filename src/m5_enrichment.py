"""m5: chunk enrichment stub.

The lab interface requires ``enrich_chunks`` returning the same number of
items as the input (in order) with ``enriched_text`` and
``auto_metadata``. When no LLM is available the function returns an empty
list, signalling to the setup script that it should fall back to the
original chunks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class EnrichedChunk:
    enriched_text: str
    auto_metadata: dict = field(default_factory=dict)


def enrich_chunks(chunks: Iterable[dict]) -> list[EnrichedChunk]:
    return []
