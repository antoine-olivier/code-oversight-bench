"""Scope authorization helper for delegated tool calls."""


def parse_scope_header(header: str) -> set[str]:
    """Split a whitespace-separated OAuth-like scope string into a set."""
    return {tok for tok in header.strip().split() if tok}


def authorize_scopes(granted_scopes: set[str], required_scopes: set[str]) -> bool:
    """Return True if and only if every required scope is present in granted_scopes.

    An empty required_scopes set is always satisfied. If any required scope is missing,
    return False.
    """
    return required_scopes.issubset(granted_scopes)


def missing_scopes(granted_scopes: set[str], required_scopes: set[str]) -> list[str]:
    """Return sorted scopes that are required but not granted."""
    return sorted(required_scopes - granted_scopes)
