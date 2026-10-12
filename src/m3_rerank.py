"""m3: cross-encoder reranker stub.

The lab requires a ``CrossEncoderReranker`` class with a ``rerank``
method. The BM25-only pipeline uses this deterministic stub that returns
the first ``top_k`` documents unchanged. A heavier neural reranker can
be plugged in here without changing the rest of the pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class RankedDoc:
    text: str
    score: float
    metadata: dict = field(default_factory=dict)


class CrossEncoderReranker:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name

    def rerank(self, question: str, docs: list[dict], top_k: int = 3) -> list[RankedDoc]:
        results: list[RankedDoc] = []
        for doc in docs[: max(top_k, 0)]:
            results.append(RankedDoc(
                text=doc.get("text", ""),
                score=float(doc.get("score", 0.0)),
                metadata=dict(doc.get("metadata", {})),
            ))
        return results
