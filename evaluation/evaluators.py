"""
evaluation/evaluators.py
LangSmith evaluator definitions.
These track agent improvement over time — the RL signal.
"""
from langsmith.evaluation import evaluate, LangChainStringEvaluator
from utils.logging import get_logger

log = get_logger(__name__)


def verdict_accuracy_evaluator(run, example) -> dict:
    """
    Evaluate forensics verdict accuracy against ground truth.
    Used when delayed ground truth becomes available (T+24hr).
    """
    predicted = run.outputs.get("verdict", "INCONCLUSIVE")
    ground_truth = example.outputs.get("ground_truth", "UNKNOWN")

    if ground_truth == "UNKNOWN":
        return {"key": "verdict_accuracy", "score": None, "comment": "No ground truth yet"}

    score = 1.0 if predicted == ground_truth else 0.0
    return {
        "key": "verdict_accuracy",
        "score": score,
        "comment": f"Predicted: {predicted}, Ground truth: {ground_truth}",
    }


def thesis_direction_evaluator(run, example) -> dict:
    """
    Evaluate Oracle thesis direction accuracy.
    Checks if risk_level direction matched actual price movement at T+7 days.
    """
    predicted_risk = run.outputs.get("risk_level", 50)
    actual_price_direction = example.outputs.get("price_direction_t7", "neutral")

    # risk > 50 predicts price increase (bearish supply = bullish price)
    predicted_direction = "up" if predicted_risk > 50 else "stable"
    correct = predicted_direction == actual_price_direction

    return {
        "key": "thesis_direction_accuracy",
        "score": 1.0 if correct else 0.0,
        "comment": f"Predicted: {predicted_direction}, Actual: {actual_price_direction}",
    }


def reasoning_bank_hit_rate_evaluator(run, example) -> dict:
    """
    Track whether the agent used a prior reasoning bank strategy.
    Higher hit rate = better memory utilisation.
    """
    strategy_source = run.outputs.get("strategy_source", "default")
    used_rb = strategy_source == "reasoning_bank"
    return {
        "key": "reasoning_bank_hit_rate",
        "score": 1.0 if used_rb else 0.0,
        "comment": f"Strategy source: {strategy_source}",
    }


def latency_evaluator(run, example) -> dict:
    """Penalise runs that exceed latency threshold."""
    latency_ms = run.outputs.get("latency_ms", 0)
    threshold = 30_000  # 30 seconds

    score = 1.0 if latency_ms <= threshold else max(0.0, 1.0 - (latency_ms - threshold) / threshold)
    return {
        "key": "latency_score",
        "score": round(score, 3),
        "comment": f"Latency: {latency_ms}ms (threshold: {threshold}ms)",
    }


def token_efficiency_evaluator(run, example) -> dict:
    """Track token usage — should decrease over time as strategies improve."""
    tokens = run.outputs.get("token_count", 0)
    baseline = example.outputs.get("baseline_tokens", 5000)

    if baseline == 0:
        return {"key": "token_efficiency", "score": None}

    efficiency = min(1.0, baseline / max(tokens, 1))
    return {
        "key": "token_efficiency",
        "score": round(efficiency, 3),
        "comment": f"Used {tokens} tokens vs baseline {baseline}",
    }


# Registry of all evaluators for LangSmith
ALL_EVALUATORS = [
    verdict_accuracy_evaluator,
    thesis_direction_evaluator,
    reasoning_bank_hit_rate_evaluator,
    latency_evaluator,
    token_efficiency_evaluator,
]
