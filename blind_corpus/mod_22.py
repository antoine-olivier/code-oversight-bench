"""Weighted aggregation helpers for benchmark metrics."""


def validate_weights(values: list[float], weights: list[float]) -> None:
    """Ensure values and weights have equal non-zero length and non-negative weights."""
    if not values or len(values) != len(weights):
        raise ValueError("Mismatched or empty inputs")
    if any(w < 0 for w in weights) or sum(weights) <= 0:
        raise ValueError("Weights must be non-negative with positive total")


def weighted_mean(values: list[float], weights: list[float]) -> float:
    """Return the weighted arithmetic mean sum(v * w) / sum(w).

    Weights are not required to sum to 1.0 beforehand.
    """
    validate_weights(values, weights)
    num = sum(v * w for v, w in zip(values, weights))
    return num / len(values)
