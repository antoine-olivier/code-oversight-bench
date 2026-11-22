"""Bounded Least-Recently-Used (LRU) cache backed by OrderedDict."""
from collections import OrderedDict


class LRUCache:
    """Fixed-capacity LRU cache where both get() and put() refresh recency."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        self.capacity = capacity
        self._data: OrderedDict[str, str] = OrderedDict()

    def get(self, key: str) -> str | None:
        """Return value for key (marking it most recently used), or None if absent."""
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key: str, value: str) -> None:
        """Insert or update key as most recently used, evicting the LEAST recently used key if full."""
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)
