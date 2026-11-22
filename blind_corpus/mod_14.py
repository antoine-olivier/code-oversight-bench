"""Sorted-array index lookup helper."""


def binary_search_index(sorted_items: list[int], target: int) -> int:
    """Return an index i such that sorted_items[i] == target, or -1 if absent.

    Must work for any position including the first and last elements.
    """
    lo = 0
    hi = len(sorted_items) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        val = sorted_items[mid]
        if val == target:
            return mid
        if val < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
