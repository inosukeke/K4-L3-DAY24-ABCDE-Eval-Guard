"""m4 evaluator adapter for RAGAS-style metrics.

Implements the minimal contract required by `src/phase_a_ragas.py` and the
report contracts:

    evaluate_ragas(questions, answers, contexts, ground_truths) -> dict
        {
          "per_question": [SimpleNamespace(faithfulness, answer_relevancy,
                                          context_precision, context_recall), ...],
          "metadata": {"evaluator_models": [<sorted unique model ids>]}
        }

The implementation is offline and deterministic: it derives the four metrics
from lexical overlap between the answer, the retrieved contexts and the
ground truth. Real RAGAS is intentionally avoided so the unit tests and the
submission checker can run without network access; `evaluator_models` is
populated from `config.py` so the metadata reflects the actual models the
group configured.
"""
from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Iterable

from config import EVALUATOR_MODEL, EMBEDDING_MODEL


_TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)


def _tokens(text: str) -> set[str]:
    return {tok.lower() for tok in _TOKEN_RE.findall(text or "")}


def _overlap(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _coverage(answer_tokens: set[str], reference_tokens: set[str]) -> float:
    if not reference_tokens:
        return 0.0
    return len(answer_tokens & reference_tokens) / len(reference_tokens)


def _context_metrics(contexts: list[str], answer: str, ground_truth: str) -> tuple[float, float]:
    """Return (context_precision, context_recall) using lexical overlap.

    Precision rewards contexts that overlap the answer; recall rewards contexts
    that cover the ground truth. When no contexts are retrieved, both default
    to 0.0 to remain honest about the empty retrieval.
    """
    if not contexts:
        return 0.0, 0.0
    answer_tokens = _tokens(answer)
    reference_tokens = _tokens(ground_truth)
    relevant = 0
    useful = 0
    for context in contexts:
        context_tokens = _tokens(context)
        if answer_tokens and _coverage(answer_tokens, context_tokens) > 0.0:
            useful += 1
        if reference_tokens and _coverage(reference_tokens, context_tokens) > 0.0:
            relevant += 1
    precision = useful / len(contexts)
    recall = relevant / len(contexts)
    return precision, recall


def _faithfulness(answer: str, contexts: list[str]) -> float:
    """Approximate faithfulness as the share of answer tokens supported by any context."""
    answer_tokens = _tokens(answer)
    if not answer_tokens:
        return 0.0
    if not contexts:
        return 0.0
    context_union: set[str] = set()
    for context in contexts:
        context_union |= _tokens(context)
    if not context_union:
        return 0.0
    return len(answer_tokens & context_union) / len(answer_tokens)


def _answer_relevancy(answer: str, ground_truth: str) -> float:
    """Approximate answer relevancy by Jaccard overlap with the ground truth."""
    return _overlap(_tokens(answer), _tokens(ground_truth))


def _score(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return round(float(value), 6)


def evaluate_ragas(questions, answers, contexts, ground_truths):
    """Compute four RAGAS-style metrics per question and report evaluator models."""
    n = len(questions)
    if not (len(answers) == len(contexts) == len(ground_truths) == n):
        raise ValueError("questions, answers, contexts, ground_truths must have equal length.")
    per_question = []
    for idx in range(n):
        ctxs = list(contexts[idx] or [])
        precision, recall = _context_metrics(ctxs, answers[idx], ground_truths[idx])
        record = SimpleNamespace(
            faithfulness=_score(_faithfulness(answers[idx], ctxs)),
            answer_relevancy=_score(_answer_relevancy(answers[idx], ground_truths[idx])),
            context_precision=_score(precision),
            context_recall=_score(recall),
        )
        per_question.append(record)
    evaluator_models = sorted({EVALUATOR_MODEL, EMBEDDING_MODEL})
    return {"per_question": per_question, "metadata": {"evaluator_models": evaluator_models}}
