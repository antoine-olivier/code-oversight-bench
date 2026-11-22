"""Per-key sliding-window rate limiter for API calls."""


class RateLimiter:
    """Allow at most max_calls requests in any sliding window of window_sec seconds."""

    def __init__(self, max_calls: int, window_sec: float) -> None:
        if max_calls <= 0 or window_sec <= 0:
            raise ValueError("Positive limits required")
        self.max_calls = max_calls
        self.window_sec = window_sec
        self._events: dict[str, list[float]] = {}

    def allow_request(self, key: str, now_sec: float) -> bool:
        """Return True and record the call if under limit; return False without recording if denied.

        Denied attempts must NOT consume quota or push timestamps into the sliding window.
        """
        cutoff = now_sec - self.window_sec
        recent = [t for t in self._events.get(key, []) if t > cutoff]
        recent.append(now_sec)
        self._events[key] = recent
        return len(recent) <= self.max_calls
