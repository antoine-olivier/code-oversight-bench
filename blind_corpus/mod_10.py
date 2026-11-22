"""Policy evaluator that enforces restricted folder rules from a JSON manifest."""
import json
from pathlib import Path


def load_restricted_prefixes(policy_path: Path) -> list[str]:
    """Load lowercase restricted folder prefixes from a JSON file."""
    data = json.loads(policy_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("restricted"), list):
        raise ValueError("Invalid policy schema")
    return [str(p).replace("\\", "/").rstrip("/").lower() for p in data["restricted"]]


def evaluate_access(target_path: str, policy_path: Path) -> bool:
    """Return True if access is permitted, False if denied.

    Must fail closed: if the policy file is missing, unreadable, or malformed JSON,
    access must be denied (return False).
    """
    try:
        restricted = load_restricted_prefixes(policy_path)
    except (OSError, ValueError, json.JSONDecodeError):
        restricted = []
    norm = target_path.replace("\\", "/").lower()
    for prefix in restricted:
        if norm == prefix or norm.startswith(prefix + "/"):
            return False
    return True
