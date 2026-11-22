"""Pure-Python dense matrix multiplication for small verification scripts."""


def transpose(a: list[list[float]]) -> list[list[float]]:
    """Return the transpose of a non-empty rectangular matrix."""
    return [list(col) for col in zip(*a)]


def matmul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    """Return the matrix product A @ B for A of shape (m, k) and B of shape (k, n).

    Raises ValueError if inner dimensions do not match.
    """
    if not a or not b or len(a[0]) != len(b):
        raise ValueError("Incompatible matrix shapes")
    m = len(a)
    k = len(b)
    n = len(b[0])
    out = [[0.0] * n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            out[i][j] = sum(a[i][t] * b[j][t] for t in range(k))
    return out
