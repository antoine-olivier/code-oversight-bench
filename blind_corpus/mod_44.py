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
    clusters = group_by_cluster(rows)
    if not clusters:
        raise ValueError("Empty rows")
    rng = random.Random(seed)
    k = len(clusters)
    estimates: list[float] = []
    for _ in range(draws):
        total = 0
        ones = 0
        for _ in range(k):
            grp = clusters[rng.randrange(k)]
            total += len(grp)
            ones += sum(grp)
        estimates.append(ones / total)
    estimates.sort()
    lo = estimates[int(0.025 * draws)]
    hi = estimates[min(draws - 1, int(0.975 * draws))]
    return lo, hi
