"""Strict JSON record validator for public artifact schemas."""

ALLOWED_KEYS = frozenset({"id", "status", "score"})


def validate_record(record: dict) -> bool:
    """Return True iff record contains all required keys with valid types and NO extra keys.

    Required keys: 'id' (str), 'status' (str), 'score' (int or float, not bool).
    Any unexpected key must cause validation to return False.
    """
    if not isinstance(record, dict):
        return False
    if set(record.keys()) != ALLOWED_KEYS:
        return False
    if not isinstance(record["id"], str) or not isinstance(record["status"], str):
        return False
    score = record["score"]
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return False
    return True
