"""Exact integer verification of spherical-code maximum inner product bounds."""


def dot_int(u: list[int], v: list[int]) -> int:
    """Return the exact integer dot product of two equal-length integer vectors."""
    return sum(a * b for a, b in zip(u, v))


def verify_max_cosine(vectors: list[list[int]], p: int, q: int) -> bool:
    """Verify in exact integer arithmetic that every distinct pair (u, v) satisfies
    (u . v) / (||u|| ||v||) <= p / q, with p >= 0 and q > 0.

    Negative dot products always satisfy the bound since p / q >= 0.
    For positive dot products, squaring yields q^2 * (u . v)^2 <= p^2 * ||u||^2 * ||v||^2.
    """
    if p < 0 or q <= 0:
        raise ValueError("Require p >= 0 and q > 0")
    norms_sq = [dot_int(v, v) for v in vectors]
    if any(ns <= 0 for ns in norms_sq):
        raise ValueError("Zero vector not allowed")
    n = len(vectors)
    for i in range(n):
        for j in range(i + 1, n):
            d = dot_int(vectors[i], vectors[j])
            if d <= 0:
                continue
            if (q * q) * (d * d) > (p * p) * norms_sq[i] * norms_sq[j]:
                return False
    return True
