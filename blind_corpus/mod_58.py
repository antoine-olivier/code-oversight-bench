"""Cluster bootstrap confidence interval for binary outcomes grouped by session."""
import random


def group_by_cluster(rows: list[tuple[str, int]]) -> list[list[int]]:
    """Group (cluster_id, outcome) pairs into a list of outcome lists per cluster."""
    buckets: dict[str, list[int]] = {}
    for cid, val in rows:
        buckets.setdefault(cid, []).append(val)
    return [buckets[k] for k in sorted(buckets)]


def cluster_bootstrap_ci(
    rows: list[tuple[str, int]], draws: int = 1000, seed: int = 0
) -> tuple[float, float]:
    """Compute a 95% cluster bootstrap confidence interval for the mean outcome.

    Each bootstrap replicate must resample whole clusters with replacement (not individual rows),
    compute the overall proportion across all observations in the drawn clusters, and return
    the (2.5%, 97.5%) percentile interval.
    """
    if not rows:
        raise ValueError("Empty rows")
    rng = random.Random(seed)
    vals = [v for _, v in rows]
    n = len(vals)
    estimates: list[float] = []
    for _ in range(draws):
        ones = sum(vals[rng.randrange(n)] for _ in range(n))
        estimates.append(ones / n)
    estimates.sort()
    lo = estimates[int(0.025 * draws)]
    hi = estimates[min(draws - 1, int(0.975 * draws))]
    return lo, hi
