"""Evaluator scoring helpers for model benchmark runs with truncated outputs."""


def is_valid_prediction(pred: str | None) -> bool:
    """Return True if a prediction is a non-empty string."""
    return isinstance(pred, str) and len(pred.strip()) > 0


def overall_accuracy(
    predictions: list[str | None], references: list[str]
) -> tuple[float, int]:
    """Compute overall accuracy treating missing/None predictions as incorrect.

    Returns (accuracy, missing_count) where accuracy = correct / len(references).
    Missing predictions must NOT be excluded from the denominator.
    """
    if not references or len(predictions) != len(references):
        raise ValueError("Mismatched or empty inputs")
    correct = 0
    missing = 0
    for pred, ref in zip(predictions, references):
        if not is_valid_prediction(pred):
            missing += 1
            continue
        if pred.strip() == ref.strip():
            correct += 1
    return correct / len(references), missing
