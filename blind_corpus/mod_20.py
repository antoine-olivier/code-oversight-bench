"""Immutable-style helper for cloning and extending tool policy dictionaries."""
import copy


def with_extra_denies(policy: dict[str, list[str]], extra: list[str]) -> dict[str, list[str]]:
    """Return a new policy dict with extra entries appended to policy['deny'].

    The caller's original policy dict and its nested lists must NOT be mutated.
    """
    cloned = copy.deepcopy(policy)
    cloned.setdefault("deny", []).extend(extra)
    return cloned
