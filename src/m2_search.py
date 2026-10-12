"""m2: lightweight BM25 retriever used as a fallback when Qdrant is unavailable.

Implements the ``HybridSearch`` contract from ``doc/PIPELINE_INTERFACE.md``
using a pure-Python BM25Okapi index. The retriever is intentionally
simple: tokenisation lower-cases and splits on non-letter characters so it
works on Vietnamese policy text without external dependencies.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

_TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)


@dataclass
class SearchHit:
    text: str
    score: float
    metadata: dict


def _tokenise(text: str) -> list[str]:
    return [tok.lower() for tok in _TOKEN_RE.findall(text or "")]


class HybridSearch:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._docs: list[dict] = []
        self._doc_tokens: list[list[str]] = []
        self._doc_lens: list[int] = []
        self._avgdl: float = 0.0
        self._df: Counter[str] = Counter()
        self._idf: dict[str, float] = {}
        self._n_docs: int = 0

    def index(self, chunks: list[dict]) -> None:
        self._docs = []
        self._doc_tokens = []
        for chunk in chunks:
            text = chunk.get("text", "")
            tokens = _tokenise(text)
            self._docs.append({"text": text, "metadata": dict(chunk.get("metadata", {}))})
            self._doc_tokens.append(tokens)

        self._doc_lens = [len(t) for t in self._doc_tokens]
        self._n_docs = len(self._docs)
        self._avgdl = (sum(self._doc_lens) / self._n_docs) if self._n_docs else 0.0

        self._df = Counter()
        for tokens in self._doc_tokens:
            for term in set(tokens):
                self._df[term] += 1

        self._idf = {}
        for term, df in self._df.items():
            self._idf[term] = math.log(1 + (self._n_docs - df + 0.5) / (df + 0.5))

    def _score_query(self, query_tokens: Iterable[str]) -> list[float]:
        scores = [0.0] * self._n_docs
        if not self._avgdl:
            return scores
        for term in query_tokens:
            idf = self._idf.get(term)
            if idf is None or idf <= 0:
                continue
            for idx, doc_tokens in enumerate(self._doc_tokens):
                tf = doc_tokens.count(term)
                if tf == 0:
                    continue
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * self._doc_lens[idx] / self._avgdl)
                scores[idx] += idf * numerator / denominator
        return scores

    def search(self, question: str, top_k: int = 20) -> list[SearchHit]:
        if not self._docs:
            return []
        query_tokens = _tokenise(question)
        if not query_tokens:
            return []
        scores = self._score_query(query_tokens)
        ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
        hits: list[SearchHit] = []
        for idx, score in ranked[:top_k]:
            if score <= 0:
                break
            doc = self._docs[idx]
            hits.append(SearchHit(text=doc["text"], score=score, metadata=doc["metadata"]))
        return hits
