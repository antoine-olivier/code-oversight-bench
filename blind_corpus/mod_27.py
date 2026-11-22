"""Closed real interval arithmetic [lo, hi] for elementary enclosure calculations."""


def is_valid_interval(iv: tuple[float, float]) -> bool:
    """Return True if lo <= hi."""
    return iv[0] <= iv[1]


def add_interval(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    """Return exact endpoint sum [a.lo + b.lo, a.hi + b.hi]."""
    return (a[0] + b[0], a[1] + b[1])


def mul_interval(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    """Return the tightest interval enclosing {x * y : x in a, y in b}.

    Must handle intervals containing negative endpoints as well as positive ones.
    """
    if not (is_valid_interval(a) and is_valid_interval(b)):
        raise ValueError("Invalid interval")
    products = (a[0] * b[0], a[0] * b[1], a[1] * b[0], a[1] * b[1])
    return (min(products), max(products))
