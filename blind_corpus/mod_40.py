"""Riemannian gradient projection onto the tangent space of the unit sphere."""
import math


def dot(u: list[float], v: list[float]) -> float:
    """Euclidean inner product of two vectors."""
    return sum(a * b for a, b in zip(u, v))


def normalize(u: list[float]) -> list[float]:
    """Scale a non-zero vector to unit Euclidean norm."""
    n = math.sqrt(dot(u, u))
    if n == 0.0:
        raise ValueError("Zero vector")
    return [c / n for c in u]


def project_tangent(x: list[float], grad: list[float]) -> list[float]:
    """Project Euclidean gradient grad onto the tangent space T_x S^(d-1) at unit vector x.

    The projected vector g_tan = grad - (grad . x) * x must be orthogonal to x (g_tan . x == 0).
    """
    unit_x = normalize(x)
    radial = dot(grad, unit_x)
    return [g + radial * u for g, u in zip(grad, unit_x)]
