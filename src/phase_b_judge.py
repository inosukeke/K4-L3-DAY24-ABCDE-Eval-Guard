from __future__ import annotations

"""Phase B: LLM-as-Judge — pairwise, swap-and-average, Cohen κ, bias analysis."""

import json
import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY, JUDGE_MODEL, HUMAN_LABELS_PATH, OPENAI_BASE_URL
from src.experiment_support import make_openai_client


@dataclass
class JudgeResult:
    question: str
    answer_a: str
    answer_b: str
    winner_pass1: str       # "A" | "B" | "tie"  (original order)
    winner_pass2: str       # "A" | "B" | "tie"  (after swap, ALREADY converted back)
    final_winner: str       # consensus after swap-and-average
    reasoning_pass1: str
    reasoning_pass2: str
    position_consistent: bool  # True if both passes agree on same answer
    scores_pass1: dict = field(default_factory=dict)  # {"A": float, "B": float}
    scores_pass2: dict = field(default_factory=dict)


PAIRWISE_SYSTEM_PROMPT = (
    "Bạn là expert đánh giá chất lượng câu trả lời RAG về chính sách công ty. "
    "Bạn chỉ dùng question, answer A, answer B và reference được cung cấp; "
    "không bị ảnh hưởng bởi vị trí của A hay B, không bị ảnh hưởng bởi độ dài. "
    "Trả về JSON hợp lệ theo đúng schema yêu cầu."
)

PAIRWISE_USER_TEMPLATE = """Bạn là expert đánh giá chất lượng câu trả lời RAG về chính sách công ty.

Tiêu chí đánh giá:
- Độ chính xác (accuracy): có khớp với thực tế chính sách tham chiếu không?
- Độ đầy đủ (completeness): có trả lời đủ ý thiết yếu của câu hỏi không?
- Tính súc tích (conciseness): có thừa thông tin không liên quan không?

Câu hỏi: {question}
Chính sách/đáp án tham chiếu: {reference}

Answer A:
{answer_a}

Answer B:
{answer_b}

Hãy chọn câu trả lời tốt hơn. Trả về JSON với schema chính xác:
{{"winner": "A" hoặc "B" hoặc "tie", "reasoning": "giải thích ngắn gọn", "scores": {{"A": 0.0-1.0, "B": 0.0-1.0}}}}
"""


def _coerce_score(value) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def _normalize_winner(value: str) -> str:
    if value in ("A", "B", "tie"):
        return value
    if isinstance(value, str):
        upper = value.strip().upper()
        if upper in ("A", "B", "TIE"):
            return "A" if upper == "A" else "B" if upper == "B" else "tie"
    return "tie"


def _normalize_pairwise_payload(payload: dict) -> dict:
    scores = payload.get("scores") or {}
    return {
        "winner": _normalize_winner(payload.get("winner", "tie")),
        "reasoning": str(payload.get("reasoning", "") or "").strip(),
        "scores": {
            "A": _coerce_score(scores.get("A", 0.0)),
            "B": _coerce_score(scores.get("B", 0.0)),
        },
    }


# ─── Task 5: Pairwise Judge ───────────────────────────────────────────────────

def pairwise_judge(question: str, answer_a: str, answer_b: str, reference: str = "") -> dict:
    """Task 5: Gọi LLM để chọn answer tốt hơn (A hoặc B) theo 3 tiêu chí.

    Tiêu chí đánh giá:
        - Độ chính xác (accuracy): có khớp với thực tế chính sách không?
        - Độ đầy đủ (completeness): có trả lời đủ câu hỏi không?
        - Tính súc tích (conciseness): có thừa / thiếu thông tin không?

    Returns:
        {"winner": "A"|"B"|"tie", "reasoning": str, "scores": {"A": float, "B": float}}
    """
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY or None, base_url=OPENAI_BASE_URL or None)
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": PAIRWISE_SYSTEM_PROMPT},
            {"role": "user", "content": PAIRWISE_USER_TEMPLATE.format(
                question=question, answer_a=answer_a, answer_b=answer_b, reference=reference)},
        ],
        response_format={"type": "json_object"},
    )
    payload = json.loads(response.choices[0].message.content)
    return _normalize_pairwise_payload(payload)


# ─── Task 6: Swap-and-Average ─────────────────────────────────────────────────

def swap_and_average(question: str, answer_a: str, answer_b: str, reference: str = "") -> JudgeResult:
    """Task 6: Chạy pairwise 2 lần (hoán đổi thứ tự), lấy kết quả nhất quán.

    Lý do: LLM thường có position bias (ưu tiên answer xuất hiện trước).
    Bằng cách swap, ta phát hiện và giảm bias này.

    Logic:
        Pass 1: judge(q, A, B) → winner_1 (trong không gian A/B)
        Pass 2: judge(q, B, A) → winner_2_raw (trong không gian B/A)
        Convert: nếu winner_2_raw="A" thì thực ra là B (vì đã swap)
        Final:   nếu winner_1 == winner_2 → final = winner_1
                 nếu khác nhau → final = "tie"
    """
    pass1 = pairwise_judge(question, answer_a, answer_b, reference=reference)
    pass2_raw = pairwise_judge(question, answer_b, answer_a, reference=reference)

    swap_map = {"A": "B", "B": "A", "tie": "tie"}
    winner_pass2 = swap_map[pass2_raw["winner"]]

    if pass1["winner"] == winner_pass2:
        final = pass1["winner"]
    else:
        final = "tie"

    position_consistent = (pass1["winner"] == winner_pass2)

    return JudgeResult(
        question=question, answer_a=answer_a, answer_b=answer_b,
        winner_pass1=pass1["winner"], winner_pass2=winner_pass2,
        final_winner=final,
        reasoning_pass1=pass1["reasoning"], reasoning_pass2=pass2_raw["reasoning"],
        position_consistent=position_consistent,
        scores_pass1=pass1["scores"],
        scores_pass2={"A": pass2_raw["scores"]["B"], "B": pass2_raw["scores"]["A"]},
    )


# ─── Task 7: Cohen's κ ────────────────────────────────────────────────────────

def cohen_kappa(judge_labels: list[int], human_labels: list[int]) -> float:
    """Task 7: Tính Cohen's κ giữa LLM judge và human labels.

    Args:
        judge_labels:  nhãn từ LLM judge (0 = bad answer, 1 = good answer)
        human_labels:  nhãn từ human_labels_10q.json

    Returns:
        κ ∈ [-1, 1]
    """
    if len(judge_labels) != len(human_labels) or not judge_labels:
        raise ValueError("judge_labels và human_labels phải cùng độ dài và không rỗng.")
    for label in (*judge_labels, *human_labels):
        if type(label) is not int or label not in (0, 1):
            raise ValueError("Labels must be integer 0 or 1.")
    n = len(judge_labels)
    observed = sum(1 for j, h in zip(judge_labels, human_labels) if j == h) / n
    chance = sum(
        (sum(1 for v in judge_labels if v == label) / n) *
        (sum(1 for v in human_labels if v == label) / n)
        for label in (0, 1)
    )
    if chance >= 1.0:
        return 0.0
    return (observed - chance) / (1.0 - chance)


# ─── Task 8: Bias Report ──────────────────────────────────────────────────────

def bias_report(judge_results: list[JudgeResult]) -> dict:
    """Task 8: Đo lường position bias và verbosity bias.

    Position bias: LLM chọn answer theo vị trí (A hay B) thay vì chất lượng.
        → Đo bằng % cases where position_consistent = False

    Verbosity bias: LLM ưu tiên answer dài hơn dù không chính xác hơn.
        → Đo bằng: trong các case A thắng, A có dài hơn B không? Tương tự cho B.

    Returns:
        {
          "total_judged": int,
          "position_bias_rate": float,        # 0-1, cao = bias nhiều
          "position_bias_count": int,
          "verbosity_bias": float,            # 0-1, > 0.6 = đáng lo ngại
          "verbosity_details": {
            "a_wins_a_longer": int,
            "b_wins_b_longer": int,
            "total_decisive": int,
          },
          "interpretation": str,
        }
    """
    total = len(judge_results)
    if total == 0:
        return {
            "total_judged": 0,
            "position_bias_rate": 0.0,
            "position_bias_count": 0,
            "verbosity_bias": 0.0,
            "verbosity_details": {"a_wins_a_longer": 0, "b_wins_b_longer": 0, "total_decisive": 0},
            "interpretation": "Không có kết quả judge để phân tích bias.",
        }

    position_bias_count = sum(1 for r in judge_results if not r.position_consistent)
    position_bias_rate = position_bias_count / total

    a_wins_a_longer = sum(
        1 for r in judge_results
        if r.final_winner == "A" and len(r.answer_a) > len(r.answer_b)
    )
    b_wins_b_longer = sum(
        1 for r in judge_results
        if r.final_winner == "B" and len(r.answer_b) > len(r.answer_a)
    )
    decisive = sum(1 for r in judge_results if r.final_winner != "tie")
    verbosity_bias = (a_wins_a_longer + b_wins_b_longer) / decisive if decisive > 0 else 0.0

    notes = []
    if position_bias_rate > 0.3:
        notes.append("position bias cao — nên dùng swap-and-average khi chấm.")
    else:
        notes.append("position bias thấp — judge ổn định giữa hai lượt.")
    if decisive > 0 and verbosity_bias > 0.6:
        notes.append("verbosity bias đáng lo ngại — cần kiểm tra nội dung trước khi kết luận.")
    elif decisive == 0:
        notes.append("không có case decisive để đo verbosity bias.")
    else:
        notes.append("verbosity bias trong ngưỡng chấp nhận được.")

    return {
        "total_judged": total,
        "position_bias_rate": round(position_bias_rate, 3),
        "position_bias_count": position_bias_count,
        "verbosity_bias": round(verbosity_bias, 3),
        "verbosity_details": {
            "a_wins_a_longer": a_wins_a_longer,
            "b_wins_b_longer": b_wins_b_longer,
            "total_decisive": decisive,
        },
        "interpretation": " ".join(notes),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from scripts.run_experiments import main
    raise SystemExit(main(["--phase", "b", *sys.argv[1:]]))
