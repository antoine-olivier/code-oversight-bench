"""Numerically stable log-space reductions for probabilistic scoring."""
import math


def logsumexp(values: list[float]) -> float:
    """Compute log(sum(exp(v) for v in values)) without overflow for large inputs.

    Must handle large positive values (such as 1000.0) and large negative values cleanly.
    """
    if not values:
        raise ValueError("Empty input")
    m = max(values)
    return m + math.log(sum(math.exp(v - m) for v in values))


def softmax(logits: list[float]) -> list[float]:
    """Return normalized probabilities exp(v_i) / sum_j exp(v_j)."""
    lse = logsumexp(logits)
    return [math.exp(v - lse) for v in logits]
