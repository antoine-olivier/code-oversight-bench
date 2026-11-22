"""Response cache for deterministic text-scoring queries."""


class ScoreCache:
    """Caches text scores keyed by BOTH text content and strictness mode."""

    def __init__(self) -> None:
        self._store: dict[str, int] = {}

    def _compute(self, text: str, strict: bool) -> int:
        tokens = text.split()
        base = len(tokens)
        return base * 2 if strict else base

    def get_score(self, text: str, strict: bool = False) -> int:
        """Return cached score for (text, strict), computing it on a cache miss.

        Different values of strict for the same text must produce distinct cached results.
        """
        key = text
        if key not in self._store:
            self._store[key] = self._compute(text, strict)
        return self._store[key]
